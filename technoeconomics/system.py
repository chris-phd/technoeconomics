#!/usr/bin/env python3

import copy
from enum import Enum
import graphviz
from typing import Optional, Type

class Flow:
    """
    A mass or energy flow between two devices, or an input/output
    to/from the system.
    """
    def __init__(self, name: str, flow_obj):
        self._name = name
        self._flow_obj = flow_obj


class Device:
    """
    The base class of a device. A device has a set of inputs and 
    outputs, representing mass or energy flow. A device may also 
    have a set of state variables.
    """
    def __init__(self, name: str):
        self._name = name

    @property
    def name(self):
        return self._name


class System:
    """
    A system is a collection of devices. It comprises everything 
    within the system boundary of the technoeconomic analysis.
    """
    def __init__(self, name: str):
        self._name = name
        self._graph_dot = graphviz.Digraph()
        self._devices = {}

        self._input_node_suffix = " __dummy_input__"
        self._output_node_suffix = " __dummy_output__"

    @property
    def name(self):
        return self._name

    def add_device(self, device: Type[Device]):
        if device.name in self._devices:
            raise ValueError(f"Device with name {device.name} already exists")
        self._devices[device.name] = copy.deepcopy(device)

        if self._input_node_suffix in device.name or self._output_node_suffix in device.name:
            self._graph_dot.node(device.name, "", shape="none", height="0.0", width="0.0")
        else:
            self._graph_dot.node(device.name)

    def remove_device(self, device_name: str):
        self._devices.pop(device_name, None)
        self._graph_dot.remove_node(device_name + self._input_node_suffix)
        self._graph_dot.remove_node(device_name + self._output_node_suffix)
        self._graph_dot.remove_node(device_name)
        self._graph_dot.remove_node(device_name + self._input_node_suffix)
        self._graph_dot.remove_node(device_name + self._output_node_suffix)

    def add_flow(self, from_device_name: Optional[str], to_device_name: Optional[str], flow: Type[Flow]):
        if from_device_name is None and to_device_name is None:
            raise ValueError("Cannot add flow without a source or destination")

        if from_device_name is None:
            from_device_name = to_device_name + self._input_node_suffix
            if from_device_name not in self._devices:
                self.add_device(Device(from_device_name))
        elif to_device_name is None:
            to_device_name = from_device_name + self._output_node_suffix
            if to_device_name not in self._devices:
                self.add_device(Device(to_device_name))

        # Add to the graph viz object
        self._graph_dot.edge(from_device_name, to_device_name)
        
    def add_system_input(self, device: Type[Device], flow: Type[Flow]):
        self.add_flow(None, device, flow)

    def add_system_output(self, device: Type[Flow], flow: Type[Flow]):
        self.add_flow(device, None, flow)

    def render(self, view=True, output_directory: Optional[str]=None):
        self._graph_dot.render(directory=output_directory, view=view)