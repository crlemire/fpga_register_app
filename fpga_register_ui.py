# -*- coding: utf-8 -*-
"""
Created on Tue Jan 30 09:01:05 2024

@author: clemire
"""

import streamlit as st
import pandas as pd
import os
import xml.etree.ElementTree as ET
import string
import math as m
import serial
import sys
import glob
from dataclasses import dataclass


class fpga_tools():

    class serial_tools():
        
        def __init__(self):
            self.standard_baud_rates = [110, 300, 600, 1200, 2400, 4800, 9600, 14400, 19200, 38400, 57600, 115200, 128000, 256000]
            self.parity_list = {'NONE':serial.PARITY_NONE, 'EVEN':serial.PARITY_EVEN, 'ODD':serial.PARITY_ODD,'MARK':serial.PARITY_MARK,'SPACE':serial.PARITY_SPACE}
            self.stop_bit_list = [1, 1.5, 2]
            self.port = ''
            self.baud = 115200
            self.parity = serial.PARITY_NONE
            self.timeout = None
            self.stop_bits = 1
            self.ser = serial.Serial()

        def serial_ports(self):
            """ Lists serial port names

            :raises EnvironmentError:
                On unsupported or unknown platforms
            :returns:
                A list of the serial ports available on the system
            """
            if sys.platform.startswith('win'):
                ports = ['COM%s' % (i + 1) for i in range(256)]
            elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
                # this excludes your current terminal "/dev/tty"
                ports = glob.glob('/dev/tty[A-Za-z]*')
            elif sys.platform.startswith('darwin'):
                ports = glob.glob('/dev/tty.*')
            else:
                raise EnvironmentError('Unsupported platform')

            result = []
            for port in ports:
                try:
                    s = serial.Serial(port)
                    s.close()
                    result.append(port)
                except (OSError, serial.SerialException):
                    pass
            return result

        def check_port(self):
            if(self.ser.is_open):
                return True
            else:
                return False

        def serial_settings(self):
            serial_columns = st.columns(4)
            for serial_column in range(len(serial_columns)):
                with serial_columns[serial_column]:
                    if(serial_column == 0):
                        self.baud = st.selectbox("Baud Rates : ", self.standard_baud_rates, index = 11)
                    elif(serial_column == 1):
                        if('COM13' in self.serial_ports()):
                            self.port = st.selectbox("Open Ports : ", self.serial_ports(), index = self.serial_ports().index('COM13'))
                        else:
                            self.port = st.selectbox("Open Ports : ", self.serial_ports())
                    elif(serial_column == 2):
                        self.stop_bits = st.selectbox("Stop Bits : ", self.stop_bit_list, index = 0)
                    elif(serial_column == 3):
                        parity_key = st.selectbox("Parities : ", self.parity_list.keys(), index = 0)
                        self.parity = self.parity_list[parity_key]

        def open_serial(self):
            self.ser.port     = self.port
            self.ser.baudrate = self.baud
            self.ser.parity   = self.parity
            self.ser.stopbits = self.stop_bits
            self.ser.timeout  = 10
            self.ser.bytesize = serial.EIGHTBITS
            self.ser.xonxoff  = False
            self.ser.rtscts   = False
            self.ser.dsrdtr   = False
            self.ser.open()

        def serial_control(self):
            control_columns = st.columns(3)
            for control_column in range(len(control_columns)):
                with control_columns[control_column]:
                    if  (control_column == 0):
                        if(st.button("Open COM Port")):
                            self.open_serial()
                    elif(control_column == 1):
                        if(st.button("Close COM Port")):
                            self.ser.close()
                    elif(control_column == 2):
                        st.write(self.ser)

        def serial_ui(self):
            with st.expander("COM Port Setings"):
                st.write("Serial Settings")
                self.serial_settings()
                st.divider()
                st.write("Serial Control")
                self.serial_control()

        def poll_register(self, poll_command):
            tx_data = bytes.fromhex(poll_command)
            self.ser.write(tx_data)
            rx_data = self.ser.read(4)
            return rx_data

        def write_register(self, register_command):
            tx_data = bytes.fromhex(register_command)
            self.ser.write(tx_data)

        def get_baud_rates(self):
            return self.standard_baud_rates

        def get_parity_list(self):
            return self.parity_list

    class xml_parse():
        def __init__(self):
            self.reg_conf_fname = 'enable_register_spec.xml'
            self.register_spec = []
            self.open_register_config()
            
        def open_register_config(self):
            reg_conf_path = os.getcwd() + '//' + self.reg_conf_fname
            config_tree = ET.parse(reg_conf_path)
            config_root = config_tree.getroot()
            print_tree = False
            
            #the root
            if(print_tree):print(config_tree, ' : ', config_root.tag)
            self.register_spec = []
            for device in config_root:
                if(print_tree):print(device.tag)
                device_attributes = []
                for device_attribute in device:
                    if(device_attribute.tag != 'module'):
                        if(print_tree):print("|-", device_attribute.tag , ' : ', device_attribute.text)
                        device_attributes.append(device_attribute.text)
                    else:
                        device_modules = []
                        for module in device_attribute:
                            if(module.tag != 'register'):
                                if(print_tree):print('|---', module.tag, ' : ', module.text)
                                device_modules.append(module.text)
                            else:
                                module_registers = []
                                for register in module:
                                    if(register.tag != 'field'):
                                        if(print_tree):print('|-----', register.tag, ' : ', register.text)
                                        module_registers.append(register.text)
                                    else:
                                        register_fields = []
                                        for field in register:
                                            if(field.tag != 'encoded_pair'):
                                                if(print_tree):print('|-------', field.tag, ' : ', field.text)
                                                register_fields.append(field.text)
                                            else:
                                                encoded_pair = []
                                                for epair in field:
                                                    if(print_tree):print('|---------', epair.tag, ' : ', epair.text)
                                                    encoded_pair.append(epair.text)
                                                register_fields.append(encoded_pair)
                                        module_registers.append(register_fields)
                                device_modules.append(module_registers)
                        device_attributes.append(device_modules)
                self.register_spec.append(device_attributes)

        def get_device_names(self):
            device_list = []
            for device in self.register_spec:
                device_list.append(device[0])
                
            return device_list
                
        def get_device_attributes(self, device_name):
            device_attributes = []
            mod_list = []

            for device in self.register_spec:
                if(device[0] == device_name): 
                    for device_attribute in device[:2]: # 0:Name 1: Address 2+:Modules
                        device_attributes.append(device_attribute)
                    for module in device[2:]:
                        mod_list.append(module[0])
                    device_attributes.append(mod_list)

            return device_attributes
        
        def get_module_attributes(self, device_name, module_name):
            module_attributes = []
            register_names = []
            
            for device in self.register_spec:
                if(device[0] == device_name):
                    for module in device[2:]:
                        if(module[0] == module_name):
                            for mod_attribute in module[:2]:
                                module_attributes.append(mod_attribute)
                            for register in module[2:]:
                                register_names.append(register[0])
                            module_attributes.append(register_names)
            
            return module_attributes
        
        def get_register_attributes(self, device_name,  module_name, register_name):
            register_attributes = []
            fields = []
            for device in self.register_spec:
                if(device[0] == device_name):
                    for module in device[2:]:
                        if(module[0] == module_name):
                            for register in module[2:]:
                                if(register[0] == register_name):
                                    for register_attribute in register[:4]:
                                        register_attributes.append(register_attribute)
                                    register_attributes[2].replace("_","")
                                    for field in register[4:]:
                                        fields.append(field[0])
                                    register_attributes.append(fields)
            
            return register_attributes
        
        def get_field_attributes(self, device_name,  module_name, register_name, field_name):
            field_attributes = []
            field_encoding = {}
            for device in self.register_spec:
                if(device[0] == device_name):
                    for module in device[2:]:
                        if(module[0] == module_name):
                            for register in module[2:]:
                                if(register[0] == register_name):
                                    for field in register[4:]:
                                        if(field[0] == field_name):
                                            for field_attribute in field[:4]:
                                                field_attributes.append(field_attribute)
                                            if(len(field) > 4):
                                                for enumeration in field[4:]:
                                                    field_encoding[enumeration[0]] = enumeration[1]
                                            field_attributes.append(field_encoding)
            return field_attributes

    def __init__(self):#FPGA Tools Init
        self.xparse = self.xml_parse()
        self.s_tools = self.serial_tools()

class enable_app():
    def __init__(self):
        self.read = '52'
        self.write = '57'
        self.field_command_type = [ 0, 2]
        self.field_address      = [ 2,10]
        self.field_command      = [10,18]
        self.field_xor          = [18,20]
        if 'ftools' not in st.session_state:
            st.session_state.ftools = fpga_tools()
        self.ftools = st.session_state.ftools
        st.set_page_config(
            page_title = "Enable FPGA Controller",
            layout="wide")
        st.write("ENABLE FPGA Controller")
        self.ftools.s_tools.serial_ui()

        #self.read_data = st.text_input('FPGA READ DATA', '00000000')
        #self.read_data = self.read_data.zfill(8).upper().replace(" ","").replace("_","")[-8:]
        #st.write('FPGA Read Data : ', self.read_data)

        self.enable_main()

    def enable_main(self):
        device_name = self.ftools.xparse.get_device_names()[0]
        device_name, device_address, module_list = self.ftools.xparse.get_device_attributes(device_name)
        modules = []
        modules = st.tabs(module_list)
        for module in range(len(modules)):
            with modules[module]:
                module_name, module_address, register_list = self.ftools.xparse.get_module_attributes(device_name, module_list[module])
                st.header(string.capwords(module_name.replace("_"," ")))
                for register in range(len(register_list)):
                    self.register_write_box(device_name, device_address, module_name, module_address, register_list, register)
                for register in range(len(register_list)):
                    self.register_read_box( device_name, device_address, module_name, module_address, register_list, register)

    def update_register_command(self, register_data, field_bits, start, stop):
        field_bits_list = list(field_bits)
        register_data_list = list(register_data)
        for index in range(len(register_data_list)):
            reverse_index = len(register_data_list) - 1 - index
            if(reverse_index >= int(start) and reverse_index <= int(stop)):
                field_index = int(stop) - reverse_index
                #field_index = reverse_index - int(start)
                register_data_list[index] = field_bits_list[field_index]
        return "".join(register_data_list)

    def xor_command_string(self, command_hex_string):
        num_command_bytes = m.ceil(len(command_hex_string)/2)
        byte_list = []
        XOR = 0
        for byte in range(num_command_bytes):
            byte_list.append(command_hex_string[byte*2:(byte*2) + 2] + ' ')
            XOR = XOR^int(command_hex_string[byte*2:(byte*2) + 2],16)
        return str(hex(XOR)).replace('0x','').zfill(2).upper()

    def redefine_fields(self, start, stop, read_register_bin):
        total_length = len(read_register_bin) - 1
        return [total_length - int(stop) ,total_length - int(start) + 1]

    def write_full_command(self, title, command):
        st.write(title, ' : ', command[self.field_command_type[0]:self.field_command_type[1]],
                          ' ', command[self.field_address[0]     :self.field_address[1]     ],
                          ' ', command[self.field_command[0]     :self.field_command[1]     ],
                          ' ', command[self.field_xor[0]         :self.field_xor[1]         ])

    def register_write_box(self, device_name, device_address, module_name, module_address, register_list, register):
        register_name, register_address, register_default, register_permission, field_list = self.ftools.xparse.get_register_attributes(device_name, module_name, register_list[register])
        full_register_address = device_address + '00' + module_address + register_address
        if(register_permission == 'R/W'):
            st.divider()#add horizontal divide
            st.write("Write : " + register_list[register])
            register_data = "00000000000000000000000000000000" # default to 0
            key = ''
            value = 0
            for field in range(len(field_list)-1):
                if(field%2 == 0):
                    column_fields = st.columns(2)
                with column_fields[field%2]:
                    field_name, field_base, field_start, field_stop, encoding_list = self.ftools.xparse.get_field_attributes(device_name, module_name, register_name, field_list[field])
                    field_length = int(field_stop) - int(field_start) + 1
                    if(field_base == 'e'):
                        key = st.selectbox(register_name + " : " + field_name, encoding_list.keys())
                        field_bits = encoding_list[key]
                    elif(field_base == '16'):
                        value = st.slider(register_name + " : " + field_name, 0, 2**field_length - 1)
                        binary_encoding = '{0:0' + str(field_length) + 'b}'
                        field_bits = binary_encoding.format(value)
                    elif(field_base == 'x'):
                        st.write(field_name)
                        binary_encoding = '{0:0' + str(field_length) + 'b}'
                        field_bits = binary_encoding.format(0)
                    register_data = self.update_register_command(register_data, field_bits, field_start, field_stop)
            write_data_hex = str(hex(int(register_data,2))).replace('0x','').zfill(8).upper()
            #st.write('Register Data    : ', write_data_hex)
            #st.write('Register Address : ', full_register_address)
            partial_write_command = self.write+full_register_address+write_data_hex
            full_write_command = partial_write_command + self.xor_command_string(partial_write_command)
            full_read_command = self.read + full_register_address + '00000000' + self.xor_command_string(self.read + full_register_address)
            #self.write_full_command("Full Write Command", full_write_command)
            #self.write_full_command("Poll Register Command", full_read_command)
            if(st.button('Configure ' + register_name , type="primary")):
                self.ftools.s_tools.write_register(full_write_command)
      
    def register_read_box(self, device_name, device_address, module_name, module_address, register_list, register):
        register_name, register_address, register_default, register_permission, field_list = self.ftools.xparse.get_register_attributes(device_name, module_name, register_list[register])
        full_register_address = device_address + '00' + module_address + register_address
        full_read_command = self.read + full_register_address + '00000000' + self.xor_command_string(self.read + full_register_address)
        read_data = '0x00000000'
        
        if(register_permission == 'R/O' or register_permission == 'R/W'):
            st.divider()#add horizontal divide
            st.write("Read : " + register_list[register])
            if(st.button("Poll " + module_name + " " + register_name, type="primary")):
                read_data = self.ftools.s_tools.poll_register(full_read_command)
            read_data_bin = bin(int(read_data, 16))[2:].zfill(32)

            #self.write_full_command("Poll Register Command", full_read_command)
            #st.write('Data Binary : ', read_data_bin)
            for field in range(len(field_list)-1):
                fields_left = len(field_list) - 2 - field
                if(field%2 == 0):
                    column_fields = st.columns(2)
                with column_fields[field%2]:
                    field_name, field_base, field_start, field_stop, encoding_list = self.ftools.xparse.get_field_attributes(device_name, module_name, register_name, field_list[field])
                    field_length_bin = int(field_stop) - int(field_start) + 1
                    field_length_hex = m.ceil(field_length_bin/4)
                    start, stop = self.redefine_fields(field_start, field_stop, read_data_bin)
                    field_data_hex = str(hex(int(read_data_bin[start:stop],2))).replace('0x','').zfill(field_length_hex).upper()
                    field_data_bin = read_data_bin[start:stop]
                    
                    if(field_base == 'e'):
                        encoding = ''
                        for key in encoding_list:
                            if(encoding_list[key] == field_data_bin):
                                encoding = key
                        st.write(field_name, ' : ', encoding)
                    elif(field_base == '16'):
                        st.write(field_name, ' : ', field_data_hex)
            

                    





app = enable_app()








