#!/usr/bin/env python
#coding: utf-8
#########################################################################################
# Developer: Deiner Zapata Silva.
# Date: 25/01/2019
# Description: Daemon to execute every time to check status of cpu and memory of a firewall using snmp.
# MIB: http://mibs.snmplabs.com/asn1/
#########################################################################################
from pysnmp.hlapi import *
from pysnmp.entity.rfc3413.oneliner import cmdgen
import datetime, time, os, threading, queue
from utils import *
#########################################################################################
cmdGen = cmdgen.CommandGenerator()
#########################################################################################
def snmp_walk(host, community, oid, port=161, column=False, num_int=4):
    #from testlib.custom_exceptions import CustomException
    for i in range(1,num_int+1):
        try:
            error_indication, error_status, error_index, var_binds = cmdGen.nextCmd(
                cmdgen.CommunityData(community),
                cmdgen.UdpTransportTarget((host, port)), 
                oid
            )
            break
        except:
            time.sleep(0.5)
            error_indication = "|{0}| snmp_walk Can't execute. Number of intent {1}x0.5 seg".format(i,host)
            print(error_indication)
            pass
    
    messages=""
    data_json = {}
    list_name = []
    list_value = []
    # Check for errors and print out results
    if error_indication:
        print("[ERROR] {0}".format(error_indication))#raise CustomException(error_indication)
        data_json.update( {'status' : 'error', "msg_err" : error_indication} )
    else:
        if error_status:
            messages = ('%s at %s' % (
                error_status.prettyPrint(),  # pylint: disable=no-member
                error_index and var_binds[int(error_index) - 1] or '?'))
            #print(messages) #raise CustomException(messages)
            data_json.update( {'status' : 'error', "msg_err" : messages} )
        else:
            if var_binds:
                for data in var_binds:
                    name , value = data[0]
                    #print( str(name) + " = " + str(value))
                    if (column) :
                        list_name.append( str(name) )
                        list_value.append( str(value) )
                    else:
                        data_json.update( { str(name) : str(value)} )
                if(column):
                    data_json.update( {'list_name' : list_name} )
                    data_json.update( {'list_value' : list_value} )
                data_json.update( {'status' : "success"} )
            else:
                messages = 'Empty Replay'
                data_json.update( {'status' : 'error', "msg_err" : messages} )
    return data_json
#########################################################################################
def thread_snmp_walk(host, community, oid, port, column, cola):
    data_json = snmp_walk(host, community, oid, port=port, column=column)
    cola.put( {oid : data_json} ) 
    return
########################################################################################
def multithread_snmp_walk(host, list_oids, community, port=161, column=True, window_delay=0.2):
    cola = queue.Queue()
    list_response = []
    list_threads = []
    for oid in list_oids:
        thread = threading.Thread( target =thread_snmp_walk , args = (host,community,oid, port, column, cola))
        thread.setDaemon(True)
        thread.start()
        time.sleep(window_delay)
        list_threads.append(thread)
    
    for process in list_threads:
        process.join()
    
    while len(list_response) < len(list_oids):
        try:
            time.sleep(0.1)
            data = cola.get_nowait()
            list_response.append(data)
        except queue.Empty: #Ejecuta hasta que la cola este vacia
            break
    
    #Ordenamos segun list_oids, porque nada me asegura que terminen de ejecutarse en el mismo orden
    list_sorted = []
    for oid in list_oids:
        for data in list_response:
            if oid in data:
                list_sorted.append( data[oid] )

    return list_sorted
#########################################################################################
def snmp_get_by_oid(host, community, oid, port=161):
    errorIndication, errorStatus, errorIndex, varBinds = cmdGen.getCmd(
        cmdgen.CommunityData(community),
        cmdgen.UdpTransportTarget((host, port)),
        oid
    )
    if errorIndication:
        print(errorIndication)
    else:
        if errorStatus:
            print('%s at %s' % (
                errorStatus.prettyPrint(),
                errorIndex and varBinds[int(errorIndex)-1] or '?'
                )
            )
        else:
            for name, val in varBinds:
                return(str(val))
#########################################################################################
def monitor_sys_info(host, community, port=161):
    oid = "iso.org.dod.internet.mgmt.mib-2.system" # 1.3.6.1.2.1.1`
    # Serial, Version, Model
    list_labels = [
                "sysDescr",
                "sysObjectID",
                "sysUpTime",
                "sysContact",
                "sysName",
                "sysLocation",
                "sysServices"]
    
    data_json = snmp_walk(host,community,oid, port=port, column=True)
    if 'list_value' in data_json :
        list_values = data_json['list_value']
    
        if(len(list_labels) != len(list_values) - 5):
            print( "[WARN ] monitor_sys_info {0} |{1}:{2}".format(host , len(list_labels), len(list_values)) )
        
        data_json = {}
        for i in range(0, len(list_labels)):
            data_json.update( {list_labels[i] : list_values[i]} )
        data_json.update( {'status' : 'success'} )
        #print_json(data_json)
        return data_json
    else:
        return {'status' : 'error'}
#########################################################################################    
def monitor_cpu_mem(host, community, port=161):    
    oid = "iso.org.dod.internet.private.enterprises.12356.101.4.1"
    list_labels = [
                "fgSysVersion",
                "fgSysMgmVdom",
                "fgSysCpuUsage",
                "fgSysMemUsage",
                "fgSysMemCapacity",
                "fgSysDiskUSage",
                "fgSysDiskCapacity",
                "fgSysSesCount",
                "fgSysLowMemUsage",
                "fgSysLowMemCapacity",
                "fgSysSesRate1",
                "fgSysSesRate10",
                "fgSysSesRate30",
                "fgSysSesRate60",
                "fgSysSes6Count",
                "fgSysSes6Rate1",
                "fgSysSes6Rate10",
                "fgSysSes6Rate30",
                "fgSysSes6Rate60",
                "fgSysUpTime"]
    
    data_json = snmp_walk(host, community, oid, port=port, column=True)
    if 'list_value' in data_json:    
        list_values = data_json['list_value']
        if(len(list_labels) != len(list_values)):
            print( "[WARN ] monitor_cpu_mem {0}".format(host) )
    
        data_json = {}
        for i in range(0, len(list_labels)):
            data_json.update( {list_labels[i] : list_values[i]} )
        data_json.update( {'status' : 'success'} )
        #print_json(data_json)
        return data_json
    else:
        return {'status' : 'error'}
#########################################################################################
def monitor_bandwidth(host, community, port=161):
    # Alias, Type, MacAddres, AdminStatus Operation Status
    oid_bandwidth = {
        "label_port" :  "1.3.6.1.2.1.31.1.1.1.1",
        "bytes_in" : "1.3.6.1.2.1.2.2.1.10",
        "bytes_out" : "1.3.6.1.2.1.2.2.1.16",
        "status" : "1.3.6.1.2.1.2.2.1.8"
    }

    dict_status = {
        "1" : "up",
        "2" : "down"
    }
    
    list_status = []
    list_labels = []
    list_in = []
    list_out = []

    list_oids = [oid_bandwidth['bytes_in'], oid_bandwidth['bytes_out']] #[oid_bandwidth['status'], oid_bandwidth['label_port']
    #[data_status, data_labels, data_in, data_out]
    list_response = multithread_snmp_walk(host, list_oids, community, port=port, column=True)
    
    data_status = list_response[0]
    #print_json(data_status)

    data_labels = list_response[1]
    #print_json(data_labels)

    data_in = list_response[2]
    #print_json(data_in)

    data_out = list_response[3]
    #print_json(data_out)
    
    if 'list_value' in data_status:
        list_status = data_status['list_value']

    if 'list_value' in data_labels:
        list_labels = data_labels['list_value']

    if 'list_value' in data_in:
        list_in = data_in['list_value']
    
    if 'list_value' in data_out:
        list_out = data_out['list_value']
    

    if(len(list_labels)!=len(list_in) and len(list_labels!=len(list_out))):
        print( "[WARN ] monitor_bandwidth {0}".format(host) )
    
    if( len(list_labels)>0 and len(list_in)>0 and len(list_out)>0 ):
        data_json = {}
        for i in range(0, len(list_labels)):
            data_json.update( 
                {
                    list_labels[i] : {
                        "in": int(list_in[i]),
                        "out": int(list_out[i]),
                        "status": dict_status[list_status[i]]
                    }
                })
        data_json.update({'status':'success'})
        #print_json(data_json)
        return data_json
    else:
        print( "[ERROR] monitor_bandwidth {0}".format(host, datetime.utcnow().isoformat()) )
        return {'status' : 'error'}

#########################################################################################
def get_data_firewall_snmp(host, community, port=161, sample_time = 15.0, old_time=0, data_to_monitoring="sys_info,bandwidth,cpu_mem"):
    start_time = time.time()
    list_monitoring = data_to_monitoring.split(",")
    data_json = {"status" : "error"}
    for index in list_monitoring:
        if index == "sys_info":
            data_json_sys_info = monitor_sys_info(host, community, port=port)
            if len(data_json_sys_info)>0 :
                data_json.update({"sys_info": data_json_sys_info})
            else:
                print("{0} [ERROR] get_data_firewall_snmp({1}) -> sys_info".format( datetime.utcnow().isoformat() , host))
        if index == "bandwidth":
            data_json_bandwidth = monitor_bandwidth(host, community, port=port)
            if len(data_json_bandwidth)>0 :
                data_json.update({"bandwidth": data_json_bandwidth})
            else:
                print("{0} [ERROR] get_data_firewall_snmp({1}) -> bandwidth".format( datetime.utcnow().isoformat() , host))
        if index == "cpu_mem":
            data_json_cpu_mem = monitor_cpu_mem(host,community, port=port)
            if len(data_json_cpu_mem)>0 :
                data_json.update({"cpu_mem" : data_json_cpu_mem})
            else:
                print("{0} [ERROR] get_data_firewall_snmp({1}) -> cpu_mem".format( datetime.utcnow().isoformat() , host))
    enlapsed_time = time.time() - start_time
    if( sample_time-enlapsed_time<0 ):
        data_aditional = {
            "devip" : host,
            "rename_index" : "snmp",
            "enlapsed_time" : "{0:4f}".format(enlapsed_time),
            "old_time" : (start_time), #old_time = start_time
            "status" : "error"
        }
        print("{0} [ERROR] get_data_firewall_snmp({1}) timeout - elapsed_time:{2:2f}".format( datetime.utcnow().isoformat() , host, enlapsed_time))
    else:
        data_aditional = {
            "sample_time" : "{0:5f}".format(start_time - old_time) ,
            "devip" : host,
            "rename_index" : "snmp",
            "enlapsed_time" : "{0:4f}".format(enlapsed_time),
            "old_time" : (start_time), #old_time = start_time
            "status": "success"
        }
        data_json.update(data_aditional)

        for index in list_monitoring:
            if index in data_json :
                if 'status' in data_json[index] :
                    if data_json[index]['status']=="error" :
                        data_json.update({"status": "error"})
                        break
        
        time.sleep(sample_time-enlapsed_time)
    #print_json(data_json)
    return data_json
#########################################################################################
if __name__ == "__main__":
    # Configuration of device
    host = '190.116.76.4'
    community = 'prueba'
    data_json = get_data_firewall_snmp(host, community, port=161,data_to_monitoring="bandwidth") #cpu_mem
    print_json(data_json)


