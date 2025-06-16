from time import sleep
import time
import subprocess
import re

try:
    input = raw_input
except NameError:
    pass

def remove_ansi_escape_sequences(string):
    ansi_escape = re.sub(r'\\x1b\[[0-?]*[ -/]*[@-~]', '', string)
    ansi_escape = re.sub(r'\x1B\[[0-?]*[ -/]*[@-~]', '', ansi_escape)
    ansi_escape = re.sub(r'(?:\\t)*|(?:\\n)*', '', ansi_escape)
    return ansi_escape

def send_aspen_subshell_command(command):

    # Specify the third-party shell executable
    shell_executable = "sudo /opt/bcm68620/example_user_appl"

    # Create a Popen object
    process = subprocess.Popen(shell_executable, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Get the command output
    stdout, stderr = process.communicate(input=b''+ str(command)+'\n')
    
    return stdout.decode()

def find_common_elements_in_arrays(array_of_arrays):
    
    starting_array = array_of_arrays[0]
    items_to_keep_array = starting_array
    items_to_keep_sub_array = []
    for current_array_index in range(1,len(array_of_arrays)):                  
        #Iterate through array for repeated items
        for repeated_item in items_to_keep_array:
            if repeated_item in array_of_arrays[current_array_index]:
                items_to_keep_sub_array.append(repeated_item)
        
        items_to_keep_array = items_to_keep_sub_array
        items_to_keep_sub_array = []

    return items_to_keep_array

#########
#
# General Interface Tests
#
#########
def get_serial_number():
    
    failures_found_array = []
    try:
        test_command_results = str(subprocess.check_output("atp_verify ", shell=True))
        test_command_results = remove_ansi_escape_sequences (test_command_results)
    
    except subprocess.CalledProcessError as e:
        test_command_results = ""
    
    # Gather Unit Data
    
    #print(test_command_results)
    
    pattern = "Serial\s*Number\s*=\s*(.*)\s*Manufacturer's\s*Code"
    
    match = re.search(pattern, test_command_results, re.S)

    if match:
        test_results = str(match.group(1)).strip()
        return test_results
        
    else:
        failures_found_array.append ("Error with atp_verify command \""+ test_command_results +"\", unexpected output")
        return "Serial Number Not Found"
    
    return "Serial Number Not Found"

def check_maxim_usb():

    failures_found_array = []
    print("\nChecking for Maxim present on USB")
    
    try:
        maxim_check_results = str(subprocess.check_output("lsusb -v -d 1238:0001|grep bcdDevice|awk \'{print$2}\'", shell=True) )
        maxim_check_results = remove_ansi_escape_sequences (maxim_check_results)
    
    except subprocess.CalledProcessError as e:
        maxim_check_results = ""
        
    if ("10.00" or "8.00") not in maxim_check_results:
        failures_found_array.append("Maxim is not present on USB, the most likely cause is interboard #2")
        
    return failures_found_array 
    
def check_cpu_spiflash_id():

    failures_found_array = []
    print("\nChecking CPU SPI Flash ID")
    
    try:
        spiflash_check_results = str(subprocess.check_output("source tiva_common.sh && auto_send_bmc_command \"50\"", shell=True) )
        spiflash_check_results = remove_ansi_escape_sequences (spiflash_check_results)
    
    except subprocess.CalledProcessError as e:
        spiflash_check_results = ""
    
    if ("CC 04 00 00 00") not in spiflash_check_results:
        failures_found_array.append("Primary SPI Flash ID not returned, this could cause NIC MAC Issues in ATP")
    
    return failures_found_array 
    
def aspen_msp430_test():

    failures_found_array = []
    print ("")
    
    for aspen_number in range(0,6):
    
        aspen_msp430_index= str ( 6 + aspen_number )
    
        print("Checking Aspen_"+str(aspen_number)+"'s MSP430 (#"+str(aspen_msp430_index)+")")
                        
        try:
            # Execute the command and get the output
            aspen_msp430_results = str(subprocess.check_output("pts.sh 250 " + aspen_msp430_index, shell=True))
            aspen_msp430_results = remove_ansi_escape_sequences (aspen_msp430_results)
            
        except subprocess.CalledProcessError as e:
            aspen_msp430_results = ""
        
        #print (aspen_msp430_results)
     
        # Pull Aspen MSP430 Voltages
        pattern = r"#1 = (\d+\.\d+).*#2 = (\d+\.\d+).*#3 = (\d+\.\d+).*#4 = (\d+\.\d+).*#5 = (\d+\.\d+).*#6 = (\d+\.\d+).*#7 = (\d+\.\d+).*#8 = (\d+\.\d+).*#9 = (\d+\.\d+)"

        match = re.search(pattern, aspen_msp430_results, re.S)

        if match:
            aspen_voltage_1 = float (match.group(1))
            aspen_voltage_2 = float (match.group(2))
            aspen_voltage_3 = float (match.group(3))
            aspen_voltage_4 = float (match.group(4))
            aspen_voltage_5 = float (match.group(5))
            aspen_voltage_6 = float (match.group(6))
            aspen_voltage_7 = float (match.group(7))
            aspen_voltage_8 = float (match.group(8))
            aspen_voltage_9 = float (match.group(9))
           
        else:
            failures_found_array.append ("Unexpected Error:Aspen_" + str(aspen_number) +" MSP430 Data Could not be pulled")
            continue
               
        # if aspen_number <= 4:
            # possible_error_location = ""
        # else:
            
            
        if aspen_voltage_7 > 5.000 or aspen_voltage_7 < 1.650:
            failures_found_array.append ("Aspen_" + str(aspen_number) + " 3_3V_ASPEN: power rail greater than 5V or less than 1.65V. Reading:" + str (aspen_voltage_7))
            continue
        if aspen_voltage_1 > 2.000 or aspen_voltage_1 < 0.400:
            failures_found_array.append ("Aspen_" + str(aspen_number) + " VDDC_ASPEN: power rail greater than 2V or less than 0.400V. Reading:" + str (aspen_voltage_1))
            continue
        if aspen_voltage_8 > 3.300 or aspen_voltage_8 < 0.900:
            failures_found_array.append ("Aspen_" + str(aspen_number) + " +1_8V_ASPEN_LPDDR4:  power rail greater than 3.3V or less than 0.9V. Reading:" + str (aspen_voltage_8))
            continue
        if aspen_voltage_9 > 2.500 or aspen_voltage_9 < 0.500:
            failures_found_array.append ("Aspen_" + str(aspen_number) + " +1_1V_ASPEN_LPDDR4: power rail greater than 2.5V or less than 0.5V. Reading:" + str (aspen_voltage_9))
            continue
        if aspen_voltage_6 > 2.500 or aspen_voltage_6 < 0.500:
            failures_found_array.append ("Aspen_" + str(aspen_number) + " VDDQ_ASPEN_LPDDR4: power rail greater than 2.5V or less than 0.5V. Reading:" + str (aspen_voltage_6))
            continue
        if aspen_voltage_3 > 2.000 or aspen_voltage_3 < 0.400:
            failures_found_array.append ("Aspen_" + str(aspen_number) + " +0_8V_ASPEN: power rail greater than 2V or less than 0.4V. Reading:" + str (aspen_voltage_3))
            continue
        if aspen_voltage_4 > 3.300 or aspen_voltage_4 < 0.900:
            failures_found_array.append ("Aspen_" + str(aspen_number) + " +1_8V_ASPEN: power rail greater than 3.3V or less than 0.9V. Reading:" + str (aspen_voltage_4))
            continue
        if aspen_voltage_2 > 2.500 or aspen_voltage_2 < 0.600:
            failures_found_array.append ("Aspen_" + str(aspen_number) + " +1_2V_ASPEN: power rail greater than 2.5V or less than 0.6V. Reading:" + str (aspen_voltage_2))
            continue
        if aspen_voltage_5 > 2.000 or aspen_voltage_5 < 0.400:
            failures_found_array.append ("Aspen_" + str(aspen_number) + " +0_85V_ASPEN: power rail greater than 2V or less than 0.400V. Reading:" + str (aspen_voltage_5))
            continue
    
    return failures_found_array

def q2a_msp430_test():

    failures_found_array = []
                        
    q2a_index= "4"
    
    print("\nChecking Q2A's MSP430 (#"+str(q2a_index)+")")
          

    try:
        # Execute the command and get the output
        q2a_msp430_results = str(subprocess.check_output("pts.sh 250 " + q2a_index, shell=True))
        q2a_msp430_results = remove_ansi_escape_sequences (q2a_msp430_results)

    except subprocess.CalledProcessError as e:
        q2a_msp430_results  = ""
    
    #print (q2a_msp430_results)
 
    # Pull Q2A MSP430 Voltages
    pattern = r"#1 = (\d+\.\d+).*#2 = (\d+\.\d+).*#3 = (\d+\.\d+).*#4 = (\d+\.\d+).*#5 = (\d+\.\d+).*#6 = (\d+\.\d+).*#7 = (\d+\.\d+).*#8 = (\d+\.\d+)"

    match = re.search(pattern, q2a_msp430_results, re.S)

    if match:
        q2a_voltage_1 = float (match.group(1))
        q2a_voltage_2 = float (match.group(2))
        q2a_voltage_3 = float (match.group(3))
        q2a_voltage_4 = float (match.group(4))
        q2a_voltage_5 = float (match.group(5))
        q2a_voltage_6 = float (match.group(6))
        q2a_voltage_7 = float (match.group(7))
        q2a_voltage_8 = float (match.group(8))
       
    else:
        failures_found_array.append ("Unexpected Error:Q2A MSP430 Data Could not be pulled")
        return failures_found_array
           
    
    if q2a_voltage_1 > 2.000 or q2a_voltage_1 < 0.400:
        failures_found_array.append ("Q2A +0_8_TM_VDDC: power rail greater than 2V or less than 0.4V. Reading:" + str (q2a_voltage_1))
        return failures_found_array
    if q2a_voltage_2 > 2.000 or q2a_voltage_2 < 0.400:
        failures_found_array.append ("Q2A +0_8V_TM_NIF_PCIE_VDD: power rail greater than 2V or less than 0.4V. Reading:" + str (q2a_voltage_2))
        return failures_found_array
    if q2a_voltage_8 > 2.000 or q2a_voltage_8 < 0.400:
        failures_found_array.append ("Q2A +0_8V_TM_NIF_PCIE_PVDD: power rail greater than 2V or less than 0.4V. Reading:" + str (q2a_voltage_8))
        return failures_found_array
    if q2a_voltage_6 > 3.300 or q2a_voltage_6 < 0.900:
        failures_found_array.append ("Q2A +1_8V_TM_DDR_PLL_AVDD_NIF: power rail greater than 3.3V or less than 0.9V. Reading:" + str (q2a_voltage_6))
        return failures_found_array
    if q2a_voltage_4 > 2.500 or q2a_voltage_4 < 0.600:
        failures_found_array.append ("Q2A +1_2V_TM_NIF_TVDD: power rail greater than 2.5V or less than 0.6V. Reading:" + str (q2a_voltage_4))
        return failures_found_array
    if q2a_voltage_3 > 2.000 or q2a_voltage_3 < 0.400:
        failures_found_array.append ("Q2A +0_88V_TM_DDR_VDDC: power rail greater than 2V or less than 0.4V. Reading:" + str (q2a_voltage_3))
        return failures_found_array
    if q2a_voltage_7 > 3.300 or q2a_voltage_7 < 0.900:
        failures_found_array.append ("Q2A +1_8V_TM_GDDR_VPP: power rail greater than 3.3V or less than 0.9V. Reading:" + str (q2a_voltage_7))
        return failures_found_array
    if q2a_voltage_5 > 2.500 or q2a_voltage_5 < 0.600:
        failures_found_array.append ("Q2A +1_35V_TM_DDR_VDDO: power rail greater than 2.5V or less than 0.6V. Reading:" + str (q2a_voltage_5))
        return failures_found_array        
        
    return failures_found_array
    
def temp_sensors_test():

    failures_found_array = []
    
    print("\nChecking Temperature Sensors")
          
    try:
        # Execute the command and get the output
        temp_sensors = str(subprocess.check_output("pts.sh 211", shell=True))
        temp_sensors = remove_ansi_escape_sequences (temp_sensors)

    except subprocess.CalledProcessError as e:
        temp_sensors  = ""
    
    #print (temp_sensors)
    
    mid_board_ambient_local_temp_dict     = {"sensor_name":"-1 Board #1 Local"      , "sensor_pattern": "\s*=\s*(\d*.\d*)\s*"   , "min_temp":"15.00", "max_temp":"50.00", "board_location":"-2"}
    mid_board_ambient_remote_temp_dict    = {"sensor_name":"-1 Board #1 Remote"     , "sensor_pattern": "\s*=\s*(\d*.\d*)\s*"   , "min_temp":"15.00", "max_temp":"50.00", "board_location":"-2"}
    mid_board_ambient2_local_temp_dict    = {"sensor_name":"-1 Board #2 Local"      , "sensor_pattern": "\s*=\s*(\d*.\d*)\s*"   , "min_temp":"15.00", "max_temp":"50.00", "board_location":"-2"}
    mid_board_ambient2_remote_temp_dict   = {"sensor_name":"-1 Board #2 Remote"     , "sensor_pattern": "\s*=\s*(\d*.\d*)\s*"   , "min_temp":"15.00", "max_temp":"50.00", "board_location":"-2"}
    mid_board_exaust_local_temp_dict      = {"sensor_name":"-1 Board #3 Local"      , "sensor_pattern": "\s*=\s*(\d*.\d*)\s*"   , "min_temp":"15.00", "max_temp":"50.00", "board_location":"-2"}
    mid_board_exaust_remote_temp_dict     = {"sensor_name":"-1 Board #3 Remote"     , "sensor_pattern": "\s*=\s*(\d*.\d*)\s*"   , "min_temp":"15.00", "max_temp":"50.00", "board_location":"-2"}
    mid_board_exaust2_local_temp_dict     = {"sensor_name":"-1 Board #3 Local"      , "sensor_pattern": "\s*=\s*(\d*.\d*)\s*"   , "min_temp":"15.00", "max_temp":"50.00", "board_location":"-2"}
    mid_board_exaust2_remote_temp_dict    = {"sensor_name":"-1 Board #3 Remote"     , "sensor_pattern": "\s*=\s*(\d*.\d*)\s*"   , "min_temp":"15.00", "max_temp":"50.00", "board_location":"-2"}
                                                                                                                            
    qumran_die_temp_dict                  = {"sensor_name":"U5001 Q2A Local"        , "sensor_pattern": "\s*=\s*(\d*.\d*)\s*"   , "min_temp":"25.00", "max_temp":"70.00", "board_location":"-2"}
    qumran_area_temp_dict                 = {"sensor_name":"U5001 Q2A Remote"       , "sensor_pattern": "\s*=\s*(\d*.\d*)\s*"   , "min_temp":"25.00", "max_temp":"70.00", "board_location":"-2"}
    bottom_board_ambient_local_temp_dict  = {"sensor_name":"U7050 Local"            , "sensor_pattern": "\s*=\s*(\d*.\d*)\s*"   , "min_temp":"15.00", "max_temp":"50.00", "board_location":"-2"}
    bottom_board_ambient_remote_temp_dict = {"sensor_name":"U7050 Remote"           , "sensor_pattern": "\s*=\s*(\d*.\d*)\s*"   , "min_temp":"15.00", "max_temp":"50.00", "board_location":"-2"}
    bottom_board_exaust_local_temp_dict   = {"sensor_name":"U7051 Local"            , "sensor_pattern": "\s*=\s*(\d*.\d*)\s*"   , "min_temp":"15.00", "max_temp":"50.00", "board_location":"-2"}
    bottom_board_exaust_remote_temp_dict  = {"sensor_name":"U7051 Remote"           , "sensor_pattern": "\s*=\s*(\d*.\d*)\s*"   , "min_temp":"15.00", "max_temp":"50.00", "board_location":"-2"}
                                                                                                                            
    pcie_switch_die_temp_dict             = {"sensor_name":"U3500 PCIe Switch Remot", "sensor_pattern": "\s*=\s*(\d*.\d*)\s*"   , "min_temp":"25.00", "max_temp":"70.00", "board_location":"-3"}
    pcie_switch_area_temp_dict            = {"sensor_name":"U3500 PCIe Switch Local", "sensor_pattern": "\s*=\s*(\d*.\d*)\s*"   , "min_temp":"15.00", "max_temp":"50.00", "board_location":"-3"}
    gp_fpga_die_temp_dict                 = {"sensor_name":"U2001 GP FPGA Local"    , "sensor_pattern": "\s*=\s*(\d*.\d*)\s*"   , "min_temp":"25.00", "max_temp":"70.00", "board_location":"-3"}
    gp_fpga_area_temp_dict                = {"sensor_name":"U2001 GP FPGA Remote"   , "sensor_pattern": "\s*=\s*(\d*.\d*)\s*"   , "min_temp":"15.00", "max_temp":"50.00", "board_location":"-3"}
    cpu_die_temp_dict                     = {"sensor_name":"Package id 0"           , "sensor_pattern": "\s*:\s*(\d*.\d*)\s*"   , "min_temp":"25.00", "max_temp":"70.00", "board_location":"-3"}
    top_board_center_local_temp_dict      = {"sensor_name":"U7050 Local"            , "sensor_pattern": "\s*=\s*(\d*.\d*)\s*"   , "min_temp":"15.00", "max_temp":"50.00", "board_location":"-2"}
    top_board_center_remote_temp_dict     = {"sensor_name":"U7050 Remote"           , "sensor_pattern": "\s*=\s*(\d*.\d*)\s*"   , "min_temp":"15.00", "max_temp":"50.00", "board_location":"-2"}
    top_board_power_local_temp_dict       = {"sensor_name":"U7051 Local"            , "sensor_pattern": "\s*=\s*(\d*.\d*)\s*"   , "min_temp":"15.00", "max_temp":"50.00", "board_location":"-2"}
    top_board_power_remote_temp_dict      = {"sensor_name":"U7051 Remote"           , "sensor_pattern": "\s*=\s*(\d*.\d*)\s*"   , "min_temp":"15.00", "max_temp":"50.00", "board_location":"-2"}
    thermistor_0_temp_dict                = {"sensor_name":"-3 Board Thermistor 0"  , "sensor_pattern": "\s*=\s*(\d*.\d*)\s*"   , "min_temp":"15.00", "max_temp":"50.00", "board_location":"-3"}
    thermistor_1_temp_dict                = {"sensor_name":"-3 Board Thermistor 1"  , "sensor_pattern": "\s*=\s*(\d*.\d*)\s*"   , "min_temp":"15.00", "max_temp":"50.00", "board_location":"-3"}
    thermistor_2_temp_dict                = {"sensor_name":"-3 Board Thermistor 2"  , "sensor_pattern": "\s*=\s*(\d*.\d*)\s*"   , "min_temp":"15.00", "max_temp":"50.00", "board_location":"-3"}
    thermistor_3_temp_dict                = {"sensor_name":"-3 Board Thermistor 3"  , "sensor_pattern": "\s*=\s*(\d*.\d*)\s*"   , "min_temp":"15.00", "max_temp":"50.00", "board_location":"-3"}
    thermistor_4_temp_dict                = {"sensor_name":"-3 Board Thermistor 4"  , "sensor_pattern": "\s*=\s*(\d*.\d*)\s*"   , "min_temp":"15.00", "max_temp":"50.00", "board_location":"-3"}
    thermistor_5_temp_dict                = {"sensor_name":"-3 Board Thermistor 5"  , "sensor_pattern": "\s*=\s*(\d*.\d*)\s*.*?", "min_temp":"15.00", "max_temp":"50.00", "board_location":"-3"}
    
    sensor_dictionary_array = [pcie_switch_area_temp_dict, pcie_switch_die_temp_dict,gp_fpga_die_temp_dict,gp_fpga_area_temp_dict,
                               top_board_center_local_temp_dict,top_board_center_remote_temp_dict,top_board_power_local_temp_dict,top_board_power_remote_temp_dict,
                               qumran_die_temp_dict,qumran_area_temp_dict,bottom_board_exaust_local_temp_dict,bottom_board_exaust_remote_temp_dict,bottom_board_ambient_local_temp_dict,bottom_board_ambient_remote_temp_dict,
                               mid_board_ambient_local_temp_dict,mid_board_ambient_remote_temp_dict,mid_board_ambient2_local_temp_dict,mid_board_ambient2_remote_temp_dict,
                               mid_board_exaust_local_temp_dict,mid_board_exaust_remote_temp_dict,mid_board_exaust2_local_temp_dict,mid_board_exaust2_remote_temp_dict,
                               thermistor_0_temp_dict,thermistor_1_temp_dict,thermistor_2_temp_dict,thermistor_3_temp_dict,thermistor_4_temp_dict,thermistor_5_temp_dict,cpu_die_temp_dict]
    
    pattern_substring = ""
    for dictionary in sensor_dictionary_array:
        pattern_substring += dictionary["sensor_name"] + dictionary["sensor_pattern"]
    
    # Pull Q2A MSP430 Voltages
    pattern = r""+ pattern_substring

    match = re.search(pattern, temp_sensors, re.S)
    
    print (pattern)
    
    for sensor_dictionary in sensor_dictionary_array:
        if match:
            sensor_reading_error= False
            sensor_dictionary_index = sensor_dictionary_array.index(sensor_dictionary)
            sensor_name = sensor_dictionary_array[sensor_dictionary_index]["sensor_name"]
            try: 
                current_sensor_reading = round(float(match.group(sensor_dictionary_index+1)),2)
            except subprocess.CalledProcessError as e:
                sensor_reading_error= True
            sensor_max_temp = round(float(sensor_dictionary_array[sensor_dictionary_index]["max_temp"]),2)
            sensor_min_temp = round(float(sensor_dictionary_array[sensor_dictionary_index]["min_temp"]),2)
            sensor_board_location= sensor_dictionary_array[sensor_dictionary_index]["board_location"]
            
            # debug
            #print ("Sensor \""+str(sensor_name)+"\" on "+str(sensor_board_location)+" board: temperature greater than "+str(sensor_max_temp)+" or less than "+str(sensor_min_temp)+". Reading:" + str(current_sensor_reading))
            
            if sensor_reading_error:
                failures_found_array.append ("Unexpected Error: Sensor \""+str(sensor_name)+"\"  Data Could not be pulled")
            elif current_sensor_reading > sensor_max_temp or current_sensor_reading < sensor_min_temp:
                failures_found_array.append ("Sensor \""+str(sensor_name)+"\" on "+str(sensor_board_location)+" board: temperature greater than "+str(sensor_max_temp)+" or less than "+str(sensor_min_temp)+". Reading:" + str(current_sensor_reading))
        else:
            failures_found_array.append ("Unexpected Error:Board Temp Sensor Data Could not be pulled")
            return failures_found_array
        
    return failures_found_array

def pcie_presence_test():
    
    print("\nChecking for Aspens, Q2A and FPGA PCIe Init")
    
    failures_found_array = []
    possible_failure_array = ["Aspen_0 not found on the PCIe BUS",
                            "Aspen_1 not found on the PCIe BUS",
                            "Aspen_2 not found on the PCIe BUS",
                            "Aspen_3 not found on the PCIe BUS",
                            "Aspen_4 not found on the PCIe BUS",
                            "Aspen_5 not found on the PCIe BUS",
                            "Q2A not found on the PCIe BUS",
                            "Beetle FPGA not found on the PCIe BUS" ]

    try:
        # Execute the command and get the output
        pcie_presence_results = str(subprocess.check_output("lspci", shell=True))
        pcie_presence_results = remove_ansi_escape_sequences (pcie_presence_results)
    
    except subprocess.CalledProcessError as e:
         pcie_presence_results  = ""
   
    # Check if devices are present on PCIe
    patterns_array = ["(03\:00.0 Multimedia controller: Broadcom Corporation Device 6865 \(rev a1\))",
                        "(04\:00.0 Multimedia controller: Broadcom Corporation Device 6865 \(rev a1\))",
                        "(05\:00.0 Multimedia controller: Broadcom Corporation Device 6865 \(rev a1\))",
                        "(06\:00.0 Multimedia controller: Broadcom Corporation Device 6865 \(rev a1\))",
                        "(07\:00.0 Multimedia controller: Broadcom Corporation Device 6865 \(rev a1\))",
                        "(08\:00.0 Multimedia controller: Broadcom Corporation Device 6865 \(rev a1\))",
                        "(09\:00.0 Ethernet controller: Broadcom Corporation Device 8485 \(rev 12\))",
                        "(0a\:00.0 Serial controller: Adtran Device 8040)"]
    count = 0
    for pattern in patterns_array:
    
        match = re.search(pattern, pcie_presence_results)

        if not match:
           failures_found_array.append (possible_failure_array[count])
           
        count += 1
      
    return failures_found_array

def fans_test():
   
    failures_found_array = []
    
    print("\nChecking Fan RPMs")
    
    possible_failure_array = ["Fan #1 RPM out of range. Expected 2000-5000RPM, Measured: ",
                            "Fan #2 RPM out of range. Expected 2000-5000RPM, Measured: ",
                            "Fan #3 RPM out of range. Expected 2000-5000RPM, Measured: ",
                            "System Fan RPM out of range. Expected 2000-5000RPM, Measured: "]

    # Execute the command and get the output
    try:
        test_command_results = str(subprocess.check_output("pts.sh 601", shell=True))
    
    except subprocess.CalledProcessError as e:
        test_command_results = ""
    
    # Gather Fan RPM Data
    pattern = "#1 .* (\d*).* #2 .* (\d*).* #3 .* (\d*).*SYSTEM FAN RPM = (\d*)"
    
    match = re.search(pattern, test_command_results, re.S)

    if match:
        test_results = [int (match.group(1)), int (match.group(2)), int (match.group(3)), int (match.group(4))]
    
    else:
        failures_found_array.append ("Error with fan command \""+ test_command +"\", unexpected output")
        return failures_found_array
        
    count = 0
    for each in test_results:
        
        if each < 2000 or each > 5000:
            failures_found_array.append (possible_failure_array[count] + str (each) + "RPM")
        
        count +=1
      
    return failures_found_array
    
def alarms_test_closed():

    failures_found_array = []
    print("\nChecking Alarm Inputs and Outputs Closed")

    positive_responses = ["yes", "Yes", "y", "Y", "YES"]
    negative_responses = ["no", "No", "n", "N", "NO"]
    skip_responses = ["skip",  "SKIP", "s", "S"]
    
    while True:
        
        try:
            user_input = input("Please plug in the alarm connector and enter yes to continue. To skip this test type <skip> or <no>. [yes/no/skip]: ")
            
        except ValueError as e:
            user_input = ""
        
        match_found_flag = False
        
        for each in negative_responses:
            if each == user_input:
                match_found_flag = True
                failures_found_array.append ("Please plug in Alarm Connector...")
                return failures_found_array
                
        for each in skip_responses:
            if each == user_input:
                match_found_flag = True
                failures_found_array.append ("SKIP_TEST")
                return failures_found_array
                
        for each in positive_responses:
            if each == user_input:
                match_found_flag = True
                
                try:
                    ## Closing Alarm Outputs
                    str(subprocess.check_output("pts.sh 401 mi 1", shell=True))
                    str(subprocess.check_output("pts.sh 401 ma 1", shell=True))
                
                except subprocess.CalledProcessError as e:
                    alarm_input_results = ""
                
                
                possible_failure_array = ["Alarm_1 Not Triggered or failed to close",
                                          "Alarm_2 Not Triggered or failed to close",
                                          "Alarm_3 Not Triggered or failed to close",
                                          "Alarm_4 Not Triggered or failed to close",
                                          "Alarm_5 Not Triggered or failed to close",
                                          "Alarm_6 Not Triggered or failed to close",
                                          "Alarm_7 Not Triggered or failed to close",
                                          "Alarm_8 Not Triggered or failed to close",
                                          "Alarm_9 Not Triggered Or Relay Output A Failed to Close",
                                          "Alarm_10 Not Triggered Or Relay Output B Failed to Close"]
                                          
                try:
                    # Execute the command and get the output
                    alarm_input_results = str(subprocess.check_output("pts.sh 400", shell=True))
                    alarm_input_results = remove_ansi_escape_sequences (alarm_input_results)
                
                except subprocess.CalledProcessError as e:
                    alarm_input_results = ""
                    
                                          
                # Check Alarm Input Trigger
                patterns_array = ["input alarm contact 1: closed",
                                  "input alarm contact 2: closed",
                                  "input alarm contact 3: closed",
                                  "input alarm contact 4: closed",
                                  "input alarm contact 5: closed",
                                  "input alarm contact 6: closed",
                                  "input alarm contact 7: closed",
                                  "input alarm contact 8: closed",
                                  "input alarm contact 9: closed",
                                  "input alarm contact 10: closed"]
                                  
                count = 0
                for pattern in patterns_array:
                
                    match = re.search(pattern, alarm_input_results)

                    if not match:
                       failures_found_array.append (possible_failure_array[count])
                       
                    count += 1
                return failures_found_array
                
        if match_found_flag == False:
                print("User entered: " + user_input + " which is not recognized.")

def alarms_test_opened():

    failures_found_array = []
    print("\nChecking Alarm Inputs and Outputs Closed")

    positive_responses = ["yes", "Yes", "y", "Y", "YES"]
    negative_responses = ["no", "No", "n", "N", "NO"]
    skip_responses = ["skip",  "SKIP", "s", "S"]
    
    while True:
        
        try:
            user_input = input("Please unplug the alarm connector and enter yes to continue. To skip this test type <skip> or <no>. [yes/no/skip]: ")
            
        except ValueError as e:
            user_input = ""
        
        match_found_flag = False
        
        for each in negative_responses:
            if each == user_input:
                match_found_flag = True
                failures_found_array.append ("Please unplug in Alarm Connector...")
                return failures_found_array
                
        for each in skip_responses:
            if each == user_input:
                match_found_flag = True
                failures_found_array.append ("SKIP_TEST")
                return failures_found_array
                
        for each in positive_responses:
            if each == user_input:
                match_found_flag = True
                try:
                    # Opening Alarm Outputs
                    str(subprocess.check_output("pts.sh 401 mi 0", shell=True))
                    str(subprocess.check_output("pts.sh 401 ma 0", shell=True))
                
                except subprocess.CalledProcessError as e:
                    alarm_input_results = ""
                

                possible_failure_array = ["Alarm_1 Triggered or Failed to Open",
                                          "Alarm_2 Triggered or Failed to Open",
                                          "Alarm_3 Triggered or Failed to Open",
                                          "Alarm_4 Triggered or Failed to Open",
                                          "Alarm_5 Triggered or Failed to Open",
                                          "Alarm_6 Triggered or Failed to Open",
                                          "Alarm_7 Triggered or Failed to Open",
                                          "Alarm_8 Triggered or Failed to Open",
                                          "Alarm_9 Triggered Or Relay Output A Failed to Open",
                                          "Alarm_10 Triggered Or Relay Output B Failed to Open"]
                                          
                try:
                    # Execute the command and get the output
                    alarm_input_results = str(subprocess.check_output("pts.sh 400", shell=True))
                    alarm_input_results = remove_ansi_escape_sequences (alarm_input_results)
                    
                except subprocess.CalledProcessError as e:
                    alarm_input_results = ""
                                          
                # Check Alarm Input Trigger
                patterns_array = ["input alarm contact 1: open",
                                  "input alarm contact 2: open",
                                  "input alarm contact 3: open",
                                  "input alarm contact 4: open",
                                  "input alarm contact 5: open",
                                  "input alarm contact 6: open",
                                  "input alarm contact 7: open",
                                  "input alarm contact 8: open",
                                  "input alarm contact 9: open",
                                  "input alarm contact 10: open"]
                                  
                count = 0
                for pattern in patterns_array:
                
                    match = re.search(pattern, alarm_input_results)

                    if not match:
                       failures_found_array.append (possible_failure_array[count])
                       
                    count += 1  
                            
                    if match_found_flag == False:
                            print("User entered: " + user_input + " which is not recognized.")
                            
                return failures_found_array
                
        if match_found_flag == False:
                print("User entered: " + user_input + " which is not recognized.")
  
    if (len(failures_found_array) >= 10 ):
        failures_found_array = ["All alarm tests failed, it's possible the loopback connector is not inserted or there is an issue with alarm power."]
               
    return failures_found_array

def aspen_ddr_test():

    failures_found_array = []
    print("\nChecking for Aspens DDR Init")
    
    possible_failure_array = ["(U3500)Aspen_0's DDR0 (U3502) Test ",
                              "(U3500)Aspen_0's DDR1 (U3501) Test ",
                              "(U3500)Aspen_0's DDR3 (U3503) Test ",
                              "(U4000)Aspen_1's DDR0 (U4002) Test ",
                              "(U4000)Aspen_1's DDR1 (U4001) Test ",
                              "(U4000)Aspen_1's DDR3 (U4003) Test ",
                              "(U4500)Aspen_2's DDR0 (U4502) Test ",
                              "(U4500)Aspen_2's DDR1 (U4501) Test ",
                              "(U4500)Aspen_2's DDR3 (U4503) Test ",
                              "(U5000)Aspen_3's DDR0 (U5002) Test ",
                              "(U5000)Aspen_3's DDR1 (U5001) Test ",
                              "(U5000)Aspen_3's DDR3 (U5003) Test ",
                              "(U1000)Aspen_4's DDR0 (U1002) Test ",
                              "(U1000)Aspen_4's DDR1 (U1001) Test ",
                              "(U1000)Aspen_4's DDR3 (U1003) Test ",
                              "(U1500)Aspen_5's DDR0 (U1502) Test ",
                              "(U1500)Aspen_5's DDR1 (U1501) Test ",
                              "(U1500)Aspen_5's DDR3 (U1503) Test "]
    
    try:
        # Execute the command and get the output
        aspen_ddr_results = str(subprocess.check_output("pts.sh 950", shell=True))
        aspen_ddr_results = remove_ansi_escape_sequences (aspen_ddr_results)
        
    except subprocess.CalledProcessError as e:
        aspen_ddr_results = ""
    
    #print("\n####\n####\n####\n" + str(aspen_ddr_results) + "\n####\n####\n####")
    
    # Check if DDR BIST is present and passed
    patterns_array = ["(ASPEN_0\s*0\/3\s*PASSED)",
                      "(ASPEN_0\s*1\/3\s*PASSED)",
                      "(ASPEN_0\s*3\/3\s*PASSED)",
                      "(ASPEN_1\s*0\/3\s*PASSED)",
                      "(ASPEN_1\s*1\/3\s*PASSED)",
                      "(ASPEN_1\s*3\/3\s*PASSED)",
                      "(ASPEN_2\s*0\/3\s*PASSED)",
                      "(ASPEN_2\s*1\/3\s*PASSED)",
                      "(ASPEN_2\s*3\/3\s*PASSED)",
                      "(ASPEN_3\s*0\/3\s*PASSED)",
                      "(ASPEN_3\s*1\/3\s*PASSED)",
                      "(ASPEN_3\s*3\/3\s*PASSED)",
                      "(ASPEN_4\s*0\/3\s*PASSED)",
                      "(ASPEN_4\s*1\/3\s*PASSED)",
                      "(ASPEN_4\s*3\/3\s*PASSED)",
                      "(ASPEN_5\s*0\/3\s*PASSED)",
                      "(ASPEN_5\s*1\/3\s*PASSED)",
                      "(ASPEN_5\s*3\/3\s*PASSED)"]
    count = 0
    for pattern in patterns_array:
    
        match = re.search(pattern, aspen_ddr_results)

        if not match:
            match2 = re.search(pattern.replace("PASSED", "FAILED"), aspen_ddr_results)
            
            if not match2:
                failures_found_array.append (str(possible_failure_array[count] + "not run due to missing log error"))
            else:
                failures_found_array.append (str(possible_failure_array[count] + "failed"))
           
        count += 1
      
    return failures_found_array

def confirm_bcmshell_operation():
    
    failures_found_array = []
    print("\nChecking for Q2A bcmshell connection")
    
    try:
        bcmshell_connection_results = str(subprocess.check_output("bcmshell echo Connection Test Passed", shell=True))
        bcmshell_connection_results = remove_ansi_escape_sequences (bcmshell_connection_results)
    
    except subprocess.CalledProcessError as e:
        bcmshell_connection_results = ""
        
    if "Connection Test Passed" not in bcmshell_connection_results:
        failures_found_array.append("Q2A bcmshell not running, it's possible the Q2A failed to start for an unknown reason")
        
    return failures_found_array 

def q2a_ddr_test():

    failures_found_array = []
    print("\nChecking for Q2A DDR Init")
                        
    try:
        # Execute the command and get the output
        q2a_ddr_results = str(subprocess.check_output("cat /var/log/traffic_manager_daemon_bcm_qumran.log", shell=True))
        q2a_ddr_results = remove_ansi_escape_sequences (q2a_ddr_results)
        
    except subprocess.CalledProcessError as e:
        q2a_ddr_results = ""
    
    #print("\n####\n####\n####\n" + str(q2a_ddr_results) + "\n####\n####\n####")

    possible_failure_array = ["Q2A DDR0 Test Failed",
                              "Q2A DDR1 Test Failed"]   
        
    # Check if DDRs passed init test
    patterns_array = ["DRC index:   0.*?(?=Byte 0 is locked and ready).*?(?=Byte 1 is locked and ready).*?(?=Byte 2 is locked and ready).*?(?=Byte 3 is locked and ready).*?(?=DDR Tuning Complete)",
                      "DRC index:   1.*?(?=Byte 0 is locked and ready).*?(?=Byte 1 is locked and ready).*?(?=Byte 2 is locked and ready).*?(?=Byte 3 is locked and ready).*?(?=DDR Tuning Complete)"]
                      
    count = 0
    for pattern in patterns_array:
    
        match = re.search(pattern, q2a_ddr_results, re.S)

        if not match:
           failures_found_array.append (possible_failure_array[count])
           
        count += 1
      
    return failures_found_array

#########
#
# LED Tests
#
#########

def set_led_color (color):
        
    if color == "RED":
        try:
            str(subprocess.check_output("pts.sh 310 0 0 0", shell=True))
            time.sleep(0.5)
            str(subprocess.check_output("pts.sh 310 0 0 1", shell=True))
                
        except ValueError as e:
            print ("Error: Could not set LED color")

    if color == "GREEN":
        try:
            str(subprocess.check_output("pts.sh 310 0 0 0", shell=True))
            str(subprocess.check_output("pts.sh 310 0 0 2", shell=True))
            str(subprocess.check_output("pts.sh 310 23 0 0", shell=True))
                
        except ValueError as e:
            print ("Error: Could not set LED color")

    elif color == "BLUE":
        try:
            str(subprocess.check_output("pts.sh 310 0 0 0", shell=True))
            str(subprocess.check_output("pts.sh 310 0 0 9", shell=True))
              
        except ValueError as e:
            print ("Error: Could not set LED color")
            
    return True

def led_test(color):

    failures_found_array = []
    
    print("\nChecking "+ str(color) +" LEDs")

    positive_responses = ["yes", "Yes", "y", "Y", "YES"]
    negative_responses = ["no", "No", "n", "N", "NO"]
    skip_responses = ["skip",  "SKIP", "s", "S"]
    
    while True:
        set_led_color(color)
        try:
            user_input = input("Are all the LEDs "+ str(color) +"? To skip this test type <skip> or <no>. [yes/no/skip]: ")
            
        except ValueError as e:
            user_input = ""
        
        match_found_flag = False
        
        for each in negative_responses:
            if each == user_input:
                match_found_flag = True
                failures_found_array.append (str(color) + " LED test not passed. Please write which LED number failed on the label")
                return failures_found_array
                
        for each in skip_responses:
            if each == user_input:
                match_found_flag = True
                failures_found_array.append ("SKIP_TEST")
                return failures_found_array
                
        for each in positive_responses:
            if each == user_input:
                match_found_flag = True
                return failures_found_array
                
        if match_found_flag == False:
                print("User entered: " + user_input + " which is not recognized.")

#########
#
# NNI Serdes Tests
#
#########

def aspen_nni_test():

    failures_found_array = []
    failures_found_sub_array = []
    print ("")
    
    for aspen_number in range(0,6):
        
        failures_found_sub_array = []
        
        print("Checking for Aspen_"+str(aspen_number)+" NNI Init")
        
        try:
            aspen_nni_results = str(subprocess.check_output("tail -n 20 /var/log/bcm686xx_"+str(aspen_number)+".log", shell=True))
            aspen_nni_results = remove_ansi_escape_sequences (aspen_nni_results)
        
        except subprocess.CalledProcessError as e:
            aspen_nni_results = ""
        
           
        #print("\n####\n####\n####\n" + str(aspen_nni_results) + "\n####\n####\n####")

        # Check all nni ports are initialized
        patterns_array = ["(internal_nni.status_changed key=\{pon_ni=0\})",
                          "(internal_nni.status_changed key=\{pon_ni=4\})",
                          "(internal_nni.status_changed key=\{pon_ni=8\})",
                          "(internal_nni.status_changed key=\{pon_ni=12\})"]
        count = 0
        for pattern in patterns_array:
        
            match = re.search(pattern, aspen_nni_results)

            if not match:
               
               failures_found_sub_array.append("Aspen_"+str(aspen_number)+" link "+ str(count) +" not enabled. Possible interboard issue")
               
            count += 1
        
        if len(failures_found_sub_array) >= 4:
            failures_found_array.append("Aspen_"+str(aspen_number)+" did not start up correctly. Check log for more info: cat /var/log/bcm686xx_"+str(aspen_number)+".log")
        else:
            failures_found_array+=failures_found_sub_array
        
    return failures_found_array
 
def q2a_aspen_nni_lock_test():

    failures_found_array = []
    print ("")
    
    try:
        q2a_aspen_nni_results = str(subprocess.check_output("bcmshell port status", shell=True))
        q2a_aspen_nni_results = remove_ansi_escape_sequences (q2a_aspen_nni_results)
    
    except subprocess.CalledProcessError as e:
        q2a_aspen_nni_results = ""
    
    for aspen_number in range(0,6):

        print("Checking for Aspen_"+str(aspen_number)+" Serdes Init at Q2A")     
           
        #print("\n####\n####\n####\n" + str(q2a_aspen_nni_results) + "\n####\n####\n####")
        
        if (aspen_number == 0):
            aspen_port_string = "[0123456789]|[1][012345]"
        elif (aspen_number == 1):
            aspen_port_string = "[1][6789]|[2][0123456789]|[3][01]"
        elif (aspen_number == 2):
            aspen_port_string = "[3][23456789]|[4][01234567]"
        elif (aspen_number == 3):
            aspen_port_string = "[4][89]|[5][0123456789]|[6][0123]"
        elif (aspen_number == 4):
            aspen_port_string = "[6][456789]|[7][0123456789]"
        elif (aspen_number == 5):
            aspen_port_string = "[8][0123456789]|[9][0123456]"

        # Check all nni ports are initialized
        matches = re.findall(r"\s*eth("+aspen_port_string+")\(("+aspen_port_string+")\)\s*\|\s*(up)\s*\|\s*25G\s*", q2a_aspen_nni_results)
        
        if matches:
            #print(matches) # prints test@xyz.com
            
            # Remove duplicates by converting the list to a set, then back to a list
            unique_matches = list(set(matches))
                          
            detected_lanes_count = len(unique_matches)
            
        else:
            detected_lanes_count = 0

        
        if int (detected_lanes_count) == 16:
        
            #print("All Lanes discovered, Aspen_"+str(aspen_number)+" to Q2A Serdes init completed")
            
            all_lanes_activated_flag = True
        
        elif int (detected_lanes_count) == 0:
        
            failures_found_array.append ("Q2A has not discovered any Aspen_"+str(aspen_number)+" lanes, its possible Aspen failed to start for some reason")  
           
        else:
            failures_found_array.append ("Q2A has discovered "+str(detected_lanes_count)+" out of 16 Aspen_"+str(aspen_number)+" lanes, possible Aspen or interboard issues")
      
    return failures_found_array
    

#########
#
# Override Interface Tests
#
#########
   
def configure_override():
    
    print("\n\nApplying configuration files and overrides, this may take a while...")
    
    try:
        str(subprocess.check_output("service_supervisor stop ngpon2_manager_vnf", shell=True)) 
        str(subprocess.check_output("service_supervisor stop netconf_ddl_watchdog", shell=True))       
        str(subprocess.check_output("service_supervisor stop traffic_manager_daemon_bcm_qumran", shell=True))
    except ValueError as e:
        print ("Error when disabling services for override config.")
    
    try:
        override_config_results = str(subprocess.check_output("service_supervisor stop -wd dev_mgmt_daemon", shell=True))

    except subprocess.CalledProcessError as e:
        override_config_results = ""
    
    try:
        str(subprocess.check_output("cp /opt/bcm68620/bcm68650_appl.bin /opt/bcm68620/bcm68650_appl.bin.bak", shell=True))

        ###Edit Folder Location Here
        str(subprocess.check_output("cp /tmp/test/bcm68650_appl_1697500590125.bin /opt/bcm68620/bcm68650_appl.bin", shell=True)) 
        str(subprocess.check_output("cp /tmp/test/config.bcm /etc/bcm/config.bcm", shell=True))
       
        str(subprocess.check_output("service_supervisor start traffic_manager_daemon_bcm_qumran", shell=True))  
        str(subprocess.check_output("service_supervisor start netconf_ddl_watchdog", shell=True))

        str(subprocess.check_output("service_supervisor start dev_mgmt_daemon", shell=True))
    except ValueError as e:
        print ("Error when re-enabling services for override config")
    

    for aspen_number in range(0,6):
    
        print ("Starting Aspen_"+str(aspen_number)+" in test mode...")
        
        send_aspen_subshell_command("/api/oper object=device sub=connect device_id=" +str(aspen_number)+ " system_mode=ae__16_x_10g ddr_test_mode=all_ddrs")
    
    print ("Continuing with test...")
    
    return True

def confirm_uplink_configuration():
    
    print("\nChecking that Q2A Uplinks were reconfigured correctly")
    
    try:
        q2a_uplink_config_results = str(subprocess.check_output("bcmshell port status", shell=True) )
        q2a_uplink_config_results = remove_ansi_escape_sequences (q2a_uplink_config_results)
    
    except subprocess.CalledProcessError as e:
        q2a_uplink_config_results = ""
    
    #print (q2a_uplink_config_results)
    
    pattern = "eth130\(130\)\s*\|\s*.*\s*\|\s*10G.*eth131\(131\)\s*\|\s*.*\s*\|\s*10G.*eth132\(132\)\s*\|\s*.*\s*\|\s*100G.*eth133\(133\)\s*\|\s*.*\s*\|\s*100G.*eth134\(134\)\s*\|\s*.*\s*\|\s*400G.*eth135\(135\)\s*\|\s*.*\s*\|\s*400G.*eth148\(148\)"
    match = re.search(pattern, q2a_uplink_config_results,re.S)
    
    if match:
        print("All Q2A Uplinks configured correctly, continuing with test...")
        return True
    else:
        print("Error: Uplinks not configured as expected, stopping test")
        return False
    
def confirm_aspen_configuration():
    
    print("\nChecking that Aspens were reconfigured successfully")
    
    all_aspens_connected_flag = False
    count = 0
    while not all_aspens_connected_flag:
        aspen_missing_flag= False
        for aspen_number in range(0,6):
            
            override_config_results = send_aspen_subshell_command("/api/get object=device device_id="+str(aspen_number)+" chip_id=yes ")

            #print (override_config_results)
            
            if ("0x68658" not in override_config_results) or ("No connection with the target system" in override_config_results):
                aspen_missing_flag= True
                print ("Not all Aspens connected after reconfig, waiting 10s and trying again...")
                count += 1
                sleep(10)
            
        if count > 15:
            print ("Not all Aspens connected after reconfig, possible UUT issue, stopping test.")
            return False

       
        all_aspens_connected_flag = not aspen_missing_flag
            
    print ("All Aspens connected after reconfig, continuing with test...")
    
    return True


def uplink_modules_present_test():

    failures_found_array = []
    
    possible_failure_array = ["Port ETH 1 not detected",
                              "Port ETH 2 not detected",
                              "Port ETH 3 not detected",
                              "Port ETH 4 not detected",
                              "Port ETH 5 not detected",
                              "Port ETH 6 not detected"]
    
    print("\nChecking that Uplink Modules are present")
    
    try:
        uplink_presence_results = str(subprocess.check_output("pts.sh 902", shell=True))
        uplink_presence_results = remove_ansi_escape_sequences (uplink_presence_results)
    
    except subprocess.CalledProcessError as e:
        uplink_presence_results = ""
    
       
    #print("\n####\n####\n####\n" + str(uplink_presence_results) + "\n####\n####\n####")

    # Check all nni ports are initialized
    patterns_array = ["(QSFPDD 1\s*x\s*((?:[^\s]+ ?)*)\s*((?:[^\s]+ ?)*)\s*((?:[^\s]+ ?)*)\s*((?:[^\s]+ ?)*)\s*((?:[^\s]+ ?)*)\s*QSFPDD 2)",
                      "(QSFPDD 2\s*x\s*((?:[^\s]+ ?)*)\s*((?:[^\s]+ ?)*)\s*((?:[^\s]+ ?)*)\s*((?:[^\s]+ ?)*)\s*((?:[^\s]+ ?)*)\s*QSFP28 1)",
                      "(QSFP28 1\s*x\s*((?:[^\s]+ ?)*)\s*((?:[^\s]+ ?)*)\s*((?:[^\s]+ ?)*)\s*((?:[^\s]+ ?)*)\s*((?:[^\s]+ ?)*)\s*QSFP28 2)",
                      "(QSFP28 2\s*x\s*((?:[^\s]+ ?)*)\s*((?:[^\s]+ ?)*)\s*((?:[^\s]+ ?)*)\s*((?:[^\s]+ ?)*)\s*((?:[^\s]+ ?)*)\s*SFP\+ 1)",
                      "(SFP\+ 1\s*x\s*((?:[^\s]+ ?)*)\s*((?:[^\s]+ ?)*)\s*((?:[^\s]+ ?)*)\s*((?:[^\s]+ ?)*)\s*((?:[^\s]+ ?)*)\s*SFP\+ 2)",
                      "(SFP\+ 2\s*x\s*((?:[^\s]+ ?)*)\s*((?:[^\s]+ ?)*)\s*((?:[^\s]+ ?)*)\s*((?:[^\s]+ ?)*)\s*((?:[^\s]+ ?)*)\s*- PON side -)"]
    count = 0
    for pattern in patterns_array:
    
        match = re.search(pattern, uplink_presence_results)

        if not match:
           
           failures_found_array.append (possible_failure_array[count])
           
        count += 1
      
    return failures_found_array

def uplinks_loopback_test():

    failures_found_array = []
    print("\nChecking Uplink Serdes Loopbacks")
   
    try:
        ## Closing Alarm Outputs
        str(subprocess.check_output("bcmshell phy prbs set 130,131,132,133 mode=phy pol=3", shell=True))
        str(subprocess.check_output("bcmshell phy prbs set 134,135 mode=phy pol=6", shell=True))
    
    except subprocess.CalledProcessError as e:
        uplink_prbs_results = ""
    
    sleep(5)
       
    possible_failure_array = ["Error with SFP28 Port 1 Receiver or SFP28 Port 2 Transmitter Connection",
                              "Error with SFP28 Port 1 Receiver or SFP28 Port 2 Transmitter Connection",
                              "Error with one or more (up to 4) of the QSFP28 port 1 Receiver or QSFP28 Port 2 Transmitter Connections",
                              "Error with one or more (up to 4) of the QSFP28 port 2 Receiver or QSFP28 Port 1 Transmitter Connections",
                              "Error with one or more (up to 8) of the QSFPDD port 1 Receiver or QSFPDD Port 2 Transmitter Connections",
                              "Error with one or more (up to 8) of the QSFPDD port 2 Receiver or QSFPDD Port 1 Transmitter Connections"]
                              
    try:
        # Execute the command and get the output
        uplink_prbs_results = str(subprocess.check_output("bcmshell phy prbs get 130,131,132,133,134,135", shell=True))
        uplink_prbs_results = remove_ansi_escape_sequences (uplink_prbs_results)
    
    except subprocess.CalledProcessError as e:
        uplink_prbs_results = ""

    
    # Check Alarm Input Trigger
    patterns_array = [r"eth130 \(lane 0\):  PRBS PASSED",
                      r"eth131 \(lane 0\):  PRBS PASSED",
                      r"eth132 \(lane ([0]|[1]|[2]|[3])\):  PRBS (PASSED)",
                      r"eth133 \(lane ([0]|[1]|[2]|[3])\):  PRBS (PASSED)",
                      r"eth134 \(lane [01234567]\).*?BER=(?:[0]|\d.\d\de-[0][56789]|\d.\d\de-[1][012345])!",
                      r"eth135 \(lane [01234567]\).*?BER=(?:[0]|\d.\d\de-[0][56789]|\d.\d\de-[1][012345])!"]
                      
    count = 0
    expected_matches_count_array = [1,1,4,4,8,8]
    for pattern in patterns_array:
    
        matches = re.findall(pattern, uplink_prbs_results)
        
        if matches:
            #print(matches) 
            # Remove duplicates by converting the list to a set, then back to a list
            unique_matches = list(set(matches))
                          
            detected_lanes_count = len(unique_matches)
            
        else:
            detected_lanes_count = 0
        

        if int (detected_lanes_count) != expected_matches_count_array[count]:           
            failures_found_array.append (possible_failure_array[count])
            
        count += 1
    
    return failures_found_array


def pon_modules_present_test():
    
    failures_found_array = []
    
    print("\nChecking that PON Modules are present")

    sfp_fpga_base_port_address = [ 200, 201, 202, 203, 204, 205, 206, 207, 
                                   210, 211, 212, 213, 214, 215, 216, 217,
                                   220, 221, 222, 223, 224, 225, 226, 227,
                                   230, 231, 232, 233, 234, 235, 236, 237,
                                   240, 241, 242, 243, 244, 245, 246, 247,
                                   250, 251, 252, 253, 254, 255, 256, 257 ]
    port_count = 1
    for port_base_address in sfp_fpga_base_port_address:
        
        try:
            str(subprocess.check_output("devpci -x 8040 -r 0 -o "+str(port_base_address)+"0C -d 0xadf0", shell=True))
            str(subprocess.check_output("devpci -x 8040 -r 0 -o "+str(port_base_address)+"08 -d 0x0000", shell=True))      
            str(subprocess.check_output("devpci -x 8040 -r 0 -o "+str(port_base_address)+"08 -d 0x0001", shell=True))
        except ValueError as e:
            print ("Error sending devpci commands for PON port I2C read")
    
        # Execute the command and get the output
        try:
            test_command_results = str(subprocess.check_output("devpci -x 8040 -r 0 -o "+str(port_base_address)+"14", shell=True))
        
        except subprocess.CalledProcessError as e:
            test_command_results = ""
        
        #print (test_command_results)
        
        # Gather PON Module I2C Data
        pattern = "Read\s*\S*: 000000(..)\s*"
        
        match = re.search(pattern, test_command_results, re.S)

        if match:
            test_results = str(match.group(1)).strip()
            if test_results != "c1":
                failures_found_array.append ("Error with getting PON Port "+str(port_count)+" I2C Data, either the module is not plugged in or there is an issue with power/i2c")
            
        else:
            failures_found_array.append ("Error with command for getting PON Port "+str(port_count)+" I2C Data, unexpected regex output")
            
        port_count += 1
        
    return failures_found_array

def generate_aspen_port_data():

    aspen_0_port_array = ["0", "1", "2", "3", "4", "5", "6", "7", 
                          "8", "9", "10", "11", "12", "13", "14", "15"]
    
    aspen_1_port_array = ["16", "17", "18", "19", "20", "21", "22", "23", 
                          "24", "25", "26", "27", "28", "29", "30", "31"] 
                                               
    aspen_2_port_array = ["32", "33", "34", "35", "36", "37", "38", "39",
                          "40", "41", "42", "43", "44", "45", "46", "47"] 
                          
    aspen_3_port_array = ["48", "49", "50", "51", "52", "53", "54", "55", 
                          "56", "57", "58", "59", "60", "61", "62", "63"] 
                          
    aspen_4_port_array = [ "64", "65", "66", "67", "68", "69", "70", "71", 
                           "72", "73", "74", "75", "76", "77", "78", "79"]
                        
    aspen_5_port_array = ["80", "81", "82", "83", "84", "85", "86", "87", 
                          "88", "89", "90", "91", "92", "93", "94", "95"]
                                                
    aspen_port_array = [aspen_0_port_array, aspen_1_port_array, aspen_2_port_array, aspen_3_port_array, aspen_4_port_array, aspen_5_port_array]
    
    
    aspen_port_dictionary = {
        '0': {"generator": "yes", "checker": "no", "pon_type":"ae_10g" },
        '1': {"generator": "no", "checker": "no", "pon_type":"ae_1g" },
        '2': {"generator": "yes", "checker": "no", "pon_type":"ae_10g" },
        '3': {"generator": "yes", "checker": "no", "pon_type":"ae_1g" },
        '4': {"generator": "yes", "checker": "no", "pon_type":"ae_10g" },
        '5': {"generator": "no", "checker": "no", "pon_type":"ae_1g" },
        '6': {"generator": "yes", "checker": "no", "pon_type":"ae_10g" },
        '7': {"generator": "yes", "checker": "no", "pon_type":"ae_1g" },
        '8': {"generator": "yes", "checker": "no", "pon_type":"ae_10g" },
        '9': {"generator": "no", "checker": "no", "pon_type":"ae_1g" },
        '10': {"generator": "yes", "checker": "no", "pon_type":"ae_10g" },
        '11': {"generator": "yes", "checker": "no", "pon_type":"ae_1g" },
        '12': {"generator": "yes", "checker": "no", "pon_type":"ae_10g" },
        '13': {"generator": "no", "checker": "no", "pon_type":"ae_1g" },
        '14': {"generator": "yes", "checker": "no", "pon_type":"ae_10g" },
        '15': {"generator": "yes", "checker": "no", "pon_type":"ae_1g"},
        '16': {"generator": "yes", "checker": "no", "pon_type":"ae_10g" },
        '17': {"generator": "no", "checker": "no", "pon_type":"ae_1g" },
        '18': {"generator": "yes", "checker": "no", "pon_type":"ae_10g" },
        '19': {"generator": "yes", "checker": "no", "pon_type":"ae_1g" },
        '20': {"generator": "yes", "checker": "no", "pon_type":"ae_10g" },
        '21': {"generator": "no", "checker": "no", "pon_type":"ae_1g" },
        '22': {"generator": "yes", "checker": "no", "pon_type":"ae_10g" },
        '23': {"generator": "yes", "checker": "no", "pon_type":"ae_1g" },
        '24': {"generator": "yes", "checker": "no", "pon_type":"ae_10g" },
        '25': {"generator": "no", "checker": "no", "pon_type":"ae_1g"},
        '26': {"generator": "yes", "checker": "no", "pon_type":"ae_10g" },
        '27': {"generator": "yes", "checker": "no", "pon_type":"ae_1g" },
        '28': {"generator": "yes", "checker": "no", "pon_type":"ae_10g" },
        '29': {"generator": "no", "checker": "no", "pon_type":"ae_1g" },
        '30': {"generator": "yes", "checker": "no", "pon_type":"ae_10g" },
        '31': {"generator": "yes", "checker": "no", "pon_type":"ae_1g" },
        '32': {"generator": "yes", "checker": "no", "pon_type":"ae_10g" },
        '33': {"generator": "no", "checker": "no", "pon_type":"ae_1g" },
        '34': {"generator": "yes", "checker": "no", "pon_type":"ae_10g" },
        '35': {"generator": "yes", "checker": "no", "pon_type":"ae_1g"},
        '36': {"generator": "yes", "checker": "no", "pon_type":"ae_10g" },
        '37': {"generator": "no", "checker": "no", "pon_type":"ae_1g" },
        '38': {"generator": "yes", "checker": "no", "pon_type":"ae_10g" },
        '39': {"generator": "yes", "checker": "no", "pon_type":"ae_1g" },
        '40': {"generator": "yes", "checker": "no", "pon_type":"ae_10g" },
        '41': {"generator": "no", "checker": "no", "pon_type":"ae_1g" },
        '42': {"generator": "yes", "checker": "no", "pon_type":"ae_10g" },
        '43': {"generator": "yes", "checker": "no", "pon_type":"ae_1g" },
        '44': {"generator": "yes", "checker": "no", "pon_type":"ae_10g" },
        '45': {"generator": "no", "checker": "no", "pon_type":"ae_1g"},
        '46': {"generator": "yes", "checker": "no", "pon_type":"ae_10g" },
        '47': {"generator": "yes", "checker": "no", "pon_type":"ae_1g" },
        '48': {"generator": "yes", "checker": "no", "pon_type":"ae_10g" },
        '49': {"generator": "no", "checker": "no", "pon_type":"ae_1g" },
        '50': {"generator": "yes", "checker": "no", "pon_type":"ae_10g" },
        '51': {"generator": "yes", "checker": "no", "pon_type":"ae_1g" },
        '52': {"generator": "yes", "checker": "no", "pon_type":"ae_10g" },
        '53': {"generator": "no", "checker": "no", "pon_type":"ae_1g" },
        '54': {"generator": "yes", "checker": "no", "pon_type":"ae_10g" },
        '55': {"generator": "yes", "checker": "no", "pon_type":"ae_1g"},
        '56': {"generator": "yes", "checker": "no", "pon_type":"ae_10g" },
        '57': {"generator": "no", "checker": "no", "pon_type":"ae_1g" },
        '58': {"generator": "yes", "checker": "no", "pon_type":"ae_10g" },
        '59': {"generator": "yes", "checker": "no", "pon_type":"ae_1g" },
        '60': {"generator": "yes", "checker": "no", "pon_type":"ae_10g" },
        '61': {"generator": "no", "checker": "no", "pon_type":"ae_1g" },
        '62': {"generator": "yes", "checker": "no", "pon_type":"ae_10g" },
        '63': {"generator": "yes", "checker": "no", "pon_type":"ae_1g" },
        '64': {"generator": "yes", "checker": "no", "pon_type":"ae_10g" },
        '65': {"generator": "no", "checker": "no", "pon_type":"ae_1g"},
        '66': {"generator": "yes", "checker": "no", "pon_type":"ae_10g" },
        '67': {"generator": "yes", "checker": "no", "pon_type":"ae_1g" },
        '68': {"generator": "yes", "checker": "no", "pon_type":"ae_10g" },
        '69': {"generator": "no", "checker": "no", "pon_type":"ae_1g" },
        '70': {"generator": "yes", "checker": "no", "pon_type":"ae_10g" },
        '71': {"generator": "yes", "checker": "no", "pon_type":"ae_1g" },
        '72': {"generator": "yes", "checker": "no", "pon_type":"ae_10g" },
        '73': {"generator": "no", "checker": "no", "pon_type":"ae_1g" },
        '74': {"generator": "yes", "checker": "no", "pon_type":"ae_10g" },
        '75': {"generator": "yes", "checker": "no", "pon_type":"ae_1g"},
        '76': {"generator": "yes", "checker": "no", "pon_type":"ae_10g" },
        '77': {"generator": "no", "checker": "no", "pon_type":"ae_1g" },
        '78': {"generator": "yes", "checker": "no", "pon_type":"ae_10g" },
        '79': {"generator": "yes", "checker": "no", "pon_type":"ae_1g" },
        '80': {"generator": "yes", "checker": "no", "pon_type":"ae_10g" },
        '81': {"generator": "no", "checker": "no", "pon_type":"ae_1g" },
        '82': {"generator": "yes", "checker": "no", "pon_type":"ae_10g" },
        '83': {"generator": "yes", "checker": "no", "pon_type":"ae_1g" },
        '84': {"generator": "yes", "checker": "no", "pon_type":"ae_10g" },
        '85': {"generator": "no", "checker": "no", "pon_type":"ae_1g"},
        '86': {"generator": "yes", "checker": "no", "pon_type":"ae_10g" },
        '87': {"generator": "yes", "checker": "no", "pon_type":"ae_1g" },
        '88': {"generator": "yes", "checker": "no", "pon_type":"ae_10g" },
        '89': {"generator": "no", "checker": "no", "pon_type":"ae_1g" },
        '90': {"generator": "yes", "checker": "no", "pon_type":"ae_10g" },
        '91': {"generator": "yes", "checker": "no", "pon_type":"ae_1g" },
        '92': {"generator": "yes", "checker": "no", "pon_type":"ae_10g" },
        '93': {"generator": "no", "checker": "no", "pon_type":"ae_1g" },
        '94': {"generator": "yes", "checker": "no", "pon_type":"ae_10g" },
        '95': {"generator": "yes", "checker": "no", "pon_type":"ae_1g"}
        
    }
    
    return aspen_port_array, aspen_port_dictionary

def start_aspen_prbs(aspen_port_dictionary={}):
            
    print ("Starting Aspen Ports for PRBS Test, this may take a while ...")
        
    for aspen_port in aspen_port_dictionary:
        prbs_type= "prbs_31"
        
        # if aspen_port_dictionary[aspen_port]["pon_type"] == "ae_1g":
            # prbs_type= "prbs_7"
            # send_aspen_subshell_command("/api/oper object=pon_interface sub=switch_pon_type pon_ni="+ aspen_port +" new_pon_type=ae_1g") 

        send_aspen_subshell_command("/a/o object=pon_interface sub=set_pon_interface_state pon_ni="+ aspen_port +" operation=active_working")         

        generator_invert = aspen_port_dictionary[aspen_port]["generator"]
        checker_invert = aspen_port_dictionary[aspen_port]["checker"]
        send_aspen_subshell_command("/a/s object=pon_interface pon_ni="+ aspen_port +"  ae={prbs_generator={polynom="+prbs_type+" error_insert=no invert="+generator_invert+" control=enable} prbs_checker={polynom="+prbs_type+" data_invert="+checker_invert+" mode=self_sync control=enable}}")
        send_aspen_subshell_command("/a/s object=pon_interface pon_ni="+ aspen_port +"  ae={prbs_generator={polynom="+prbs_type+" error_insert=no invert="+generator_invert+" control=disable} prbs_checker={polynom="+prbs_type+" data_invert="+checker_invert+" mode=self_sync control=disable}}")
            
        send_aspen_subshell_command("/a/s object=pon_interface pon_ni="+ aspen_port +"  ae={prbs_generator={polynom="+prbs_type+" error_insert=no invert="+generator_invert+" control=enable}}")
    
    print ("Enabling generators ...")
    for aspen_port in aspen_port_dictionary:
        prbs_type= "prbs_31"
        
        # if aspen_port_dictionary[aspen_port]["pon_type"] == "ae_1g":
            # prbs_type= "prbs_7"
        
        send_aspen_subshell_command("/a/s object=pon_interface pon_ni="+ aspen_port +"  ae={prbs_checker={polynom="+prbs_type+" data_invert="+checker_invert+" mode=self_sync control=enable}}")

    return

def get_aspen_prbs_results(aspen_port_dictionary={}):
    
    print ("Getting results from Aspen PRBS Test ...")
    
    for aspen_port in aspen_port_dictionary:
        generator_invert = aspen_port_dictionary[aspen_port]["generator"]
        checker_invert = aspen_port_dictionary[aspen_port]["checker"]
        returned_text = send_aspen_subshell_command("/a/g object=pon_interface pon_ni="+aspen_port+"  state ae={prbs_generator prbs_checker prbs_status}")
        
        lock_state = re.search("lock_state=(\S*)\s", returned_text, re.S).group(1)
        error_counts = re.search("error_counts=(\S*)\s", returned_text, re.S).group(1)
        
        aspen_port_dictionary[aspen_port]["lock_state"]=lock_state
        aspen_port_dictionary[aspen_port]["error_count"]=error_counts

    return aspen_port_dictionary

def pon_loopback_test():
    
    pon_loopback_test_repeat_count = 3
    
    failures_found_array =[]
    
    print("\nChecking PON Serdes Loopbacks " + str(pon_loopback_test_repeat_count) + " time(s)")

    aspen_port_array, aspen_port_dictionary = generate_aspen_port_data()
    
    test_result_hold = []
    for test_number in range (0,pon_loopback_test_repeat_count):
    
        start_aspen_prbs(aspen_port_dictionary)
        
        #print("Running PRBS Test for 100 seconds")
        #sleep(100)

        aspen_port_dictionary = get_aspen_prbs_results(aspen_port_dictionary)
         
        test_failed_flag = False
        for aspen_number in range(len(aspen_port_array)):
            for port in range(len(aspen_port_array[aspen_number])): 
                port_test_failed_flag = False
                
                max_error_count = 65000
            
                olt_port=aspen_port_array[aspen_number][port]
                faceplate_port = (aspen_number*8) + (int(port/2)) + 1
                
                lock_state = aspen_port_dictionary[olt_port]["lock_state"]
                error_count = int(aspen_port_dictionary[olt_port]["error_count"])
                
                end_message = ""
                primary_fail_flag=False
                secondary_fail_flag=False
                if ((port+1)%2) == 1:
                    lane_number = "PRI"
                    
                    lock_state_sec = aspen_port_dictionary[str(int(olt_port) + 1)]["lock_state"]
                    error_count_sec = int(aspen_port_dictionary[str(int(olt_port)+1)]["error_count"])
                    if (lock_state == "unlocked" or error_count > max_error_count): primary_fail_flag = True
                    if (lock_state_sec == "unlocked" or error_count_sec > max_error_count): secondary_fail_flag = True
                    if (primary_fail_flag and secondary_fail_flag):
                        end_message = "Both primary and secondary seem to be having issues. Consider replacing module"
                elif ((port+1)%2) == 0:    
                    lane_number = "SEC"
                    
                    lock_state_pri = aspen_port_dictionary[str(int(olt_port)-1)]["lock_state"]
                    error_count_pri = int(aspen_port_dictionary[str(int(olt_port)-1)]["error_count"])
                    if (lock_state_pri == "unlocked" or error_count_pri > max_error_count): primary_fail_flag = True
                    if (lock_state == "unlocked" or error_count > max_error_count): secondary_fail_flag = True
                    if (primary_fail_flag and secondary_fail_flag):
                        end_message = "Both primary and secondary seem to be having issues. Consider replacing module"
                
                if (lock_state == "unlocked" or  error_count > max_error_count):
                    port_test_failed_flag = True
                    test_failed_flag = True
                    failures_found_array.append ("Aspen_"+str(aspen_number) + " Port " + str(faceplate_port) +" " + lane_number +" Lane status: " + str(lock_state) + " with " + str(error_count) + " errors " + end_message)
        
        test_result_hold.append(failures_found_array)
        print(failures_found_array)
        failures_found_array = []
    
    print (test_result_hold)
    average_failures_found_array = find_common_elements_in_arrays(test_result_hold)
    print (average_failures_found_array)
        
    # if test_failed_flag:
        # print("")
        # print("ASPEN PON PRBS TEST: FAILED")
        # print("")
    
    # else:
        # print("")
        # print("ASPEN PON PRBS TEST: PASSED")
        # print("")
        
    return average_failures_found_array
  
#########
#
# User Interaction Script Functions
#
#########

def run_test_with_user_input (uut_serial_number, test_function, argument_1=""):

    positive_responses = ["yes", "Yes", "y", "Y", "YES"]
    negative_responses = ["no", "No", "n", "N", "NO", "skip",  "SKIP", "s", "S"]
    exit_responses = ["exit", "Exit", "EXIT", "quit", "Quit", "QUIT", "end", "End", "END"]
    
    
    if argument_1 == "":
        function_return_array = test_function()
    else:
        function_return_array = test_function(argument_1)
    
    end_test_flag = True

    loop_continue_flag = True
    while loop_continue_flag:
    
        if (len(function_return_array) > 0):
            if function_return_array[0] == "SKIP_TEST":
                print("Error: Sub-test skipped by user.")
                return "SUB-TEST_FAILED"
                
        if (len(function_return_array) > 0):
            print ("####################### - ERROR: The following test failures were found:  - ############################ ")
            
            for test_failure in function_return_array:
                print (test_failure)
                
            print ("####################### -------- END ERROR MESSAGE for SN:"+ str(uut_serial_number) +" ---------- ############################\n")
            
            try:
                user_input = input("Would you like to run this test again? To skip this test type <skip> or <no>. To exit program type <exit>.[yes/no/skip/exit]: ")
                
            except ValueError as e:
                user_input = ""
            
            match_found_flag = False
            
            for each in exit_responses:
                if each == user_input:
                    match_found_flag = True
                    loop_continue_flag = False
                    return "END_TEST"
            
            for each in negative_responses:
                if each == user_input:
                    match_found_flag = True
                    loop_continue_flag = False
                    return "SUB-TEST_FAILED"
                    
            for each in positive_responses:
                if each == user_input:
                    match_found_flag = True
                    end_test_flag = False
                    if argument_1 == "":
                        function_return_array = test_function()
                    else:
                        function_return_array = test_function(argument_1)
                        
            if match_found_flag == False:
                print("User entered: " + user_input + " which is not recognized.")
                
        
        else:
            loop_continue_flag = False
            print ("SUB-TEST PASSED")
    
    return "SUB-TEST_PASSED"

################################################################################################################################
#-------------------------------------------------------------------------------------------------------------------------------
# 
# MAIN TO DO: Tell which board likely to have issue. Tell which alarm pin likely to have issue, add usb test, possible cause for all uplinks not seen on I2C, add shared PG tests
#
#-------------------------------------------------------------------------------------------------------------------------------
################################################################################################################################


########################################
#
# Script Start
#
########################################

print("\n##### - OLT Starting Script - ##### ")
start_time = time.time()

uut_serial_number = get_serial_number()

all_tests_passed_flag = True
test_fail_flag = "SUB-TEST_FAILED"
end_test_flag = "END_TEST"
while True:


    #########
    #
    # Begin LED Tests
    #
    #########
    print("LED TESTS of " + str(uut_serial_number) + " starting...")
    general_interface_test_array = [[led_test, "RED"],[led_test, "GREEN"],[led_test, "BLUE"]]
    
    for test in general_interface_test_array:
        
        function = test[0]
        argument = test[1]
        
        test_result = run_test_with_user_input (uut_serial_number,function, argument)
        if (test_result == test_fail_flag) : all_tests_passed_flag = False 
        if (test_result == end_test_flag): break 
    
    if test_result == end_test_flag:
        break

    #########
    #
    # Begin general interface section
    #
    #########


    general_interface_test_array = [check_maxim_usb, check_cpu_spiflash_id, aspen_msp430_test, q2a_msp430_test, temp_sensors_test, pcie_presence_test, fans_test, alarms_test_closed, alarms_test_opened, aspen_ddr_test, q2a_ddr_test,]
    
    for test in general_interface_test_array:
        test_result = run_test_with_user_input (uut_serial_number,test)
        if (test_result == test_fail_flag) : all_tests_passed_flag = False 
        if (test_result == end_test_flag): break 
    
    if test_result == end_test_flag:
        break

  

    #########
    #
    # Begin nni section
    #
    #########
    
    bcmshell_connection_failures_array = confirm_bcmshell_operation()
    if (len (bcmshell_connection_failures_array) == 0):
        print ("Connection to bcmshell confirmed, continuing with test...")
        
        test_result = run_test_with_user_input (uut_serial_number, aspen_nni_test)
        if (test_result == test_fail_flag) : all_tests_passed_flag = False 
        if (test_result == end_test_flag): break 
        
        test_result = run_test_with_user_input (uut_serial_number, q2a_aspen_nni_lock_test)
        if (test_result == test_fail_flag) : all_tests_passed_flag = False 
        if (test_result == end_test_flag): break 
        
    else:
        print (bcmshell_connection_failures_array)
        print ("\nError: Skipping Q2A and Aspen NNI Tests since the bcmshell did not connect")
        all_tests_passed_flag = False 


    #########
    #
    # Begin override section
    #
    #########

    # pon_modules_present_flag=True
    # test_result = run_test_with_user_input (uut_serial_number, pon_modules_present_test)
    # if (test_result == test_fail_flag):
        # pon_modules_present_flag=False
        # all_tests_passed_flag = False 
    # if (test_result == end_test_flag): break 
    


    uplink_modules_present_flag=True
    test_result = run_test_with_user_input (uut_serial_number, uplink_modules_present_test)
    if (test_result == test_fail_flag):
        uplink_modules_present_flag=False
        all_tests_passed_flag = False 
    if (test_result == end_test_flag): break 

    # configure_override()


    # bcmshell_connection_failures_array = confirm_bcmshell_operation()
    # if (len (bcmshell_connection_failures_array) == 0):
        # print ("Connection to bcmshell confirmed, continuing with test...")
        
        # uplink_configuration_applied_correctly_flag = confirm_uplink_configuration()
        # if (uplink_configuration_applied_correctly_flag):
            # if (uplink_modules_present_flag):
                # test_result = run_test_with_user_input (uut_serial_number, uplinks_loopback_test)
                # if (test_result == test_fail_flag) : all_tests_passed_flag = False 
                # if (test_result == end_test_flag): break 
            # else:
                # print("\nError: Skipping Uplink Loopback Test since not all modules inserted")
                # all_tests_passed_flag = False 
        # else:
            # print ("\nError: Skipping Uplink Loopback Test since Uplink ports were not configured correctly")
            # all_tests_passed_flag = False 

    # else:
        # print ("\nError: Skipping Q2A Uplink Loopback Test since the bcmshell did not connect")
        # all_tests_passed_flag = False 



    # aspen_configuration_applied_correctly_flag = confirm_aspen_configuration()
    # if (aspen_configuration_applied_correctly_flag):
        # if (pon_modules_present_flag):
            # test_result = run_test_with_user_input (uut_serial_number, pon_loopback_test)
            # if (test_result == test_fail_flag) : all_tests_passed_flag = False 
            # if (test_result == end_test_flag): break 
        # else:
            # print("\nWarning: Skipping PON Loopback Test since not all modules inserted")
            # #all_tests_passed_flag = False 
    # else:
        # print ("\nError: Skipping PON Loopback Test since not all Aspens were configured correctly")
        # all_tests_passed_flag = False 

    
    #Exit Loop since test is completed
    break
    

########################################
#
# Script END
#
########################################

if test_result == end_test_flag:
    print ("\n\n##### - ERROR: USER EXITED TEST, POSSIBLE TEST FAILURES - #####")

elif all_tests_passed_flag:
    print ("\n\n\n\n###########################################################################################")
    print ("\n\n##### - Test Completed: ALL TESTS PASSED - #####")
    print ("##### - Test Completed: ALL TESTS PASSED - #####")
    print ("##### - Test Completed: ALL TESTS PASSED - #####")
    print ("##### - Test Completed: ALL TESTS PASSED - #####")
    print ("##### - Test Completed: ALL TESTS PASSED - #####")
    print ("\n\n###########################################################################################")

else:
    print ("\n\n\n\n###########################################################################################")
    print ("\n\n##### - Test Completed: TEST FAILED, FAILURES FOUND - #####")
    print ("##### - Test Completed: TEST FAILED, FAILURES FOUND - #####")
    print ("##### - Test Completed: TEST FAILED, FAILURES FOUND - #####")
    print ("##### - Test Completed: TEST FAILED, FAILURES FOUND - #####")
    print ("##### - Test Completed: TEST FAILED, FAILURES FOUND - #####")
    print ("\n\n\###########################################################################################")
    

# Calculate the Script Run Time
end_time = time.time()
elapsed_time = end_time - start_time

# Convert the elapsed time to hours, minutes, and seconds
hours, rem = divmod(elapsed_time, 3600)
minutes, seconds = divmod(rem, 60)

# Print the elapsed time in hh:mm:ss format
print("##### - Serial Number = " + str(uut_serial_number))
print("##### - Test Completed in {:0>2}:{:0>2}:{:05.2f} - #####".format(int(hours), int(minutes), seconds))
print("Please contact HW4 at hwareteam4@adtran.com for any issues or suggestions on possible failure causes for this script")
