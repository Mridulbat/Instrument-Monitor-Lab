"""Read-only local Modbus TCP subset: FC03, six unsigned holding registers."""
import socket
import struct

def receive(sock,count):
    data=b''
    while len(data)<count:
        part=sock.recv(count-len(data))
        if not part:raise ConnectionError('Incomplete Modbus frame')
        data+=part
    return data

def read_registers(port=15020):
    with socket.create_connection(('127.0.0.1',port),timeout=1) as sock:
        transaction=1
        sock.sendall(struct.pack('>HHHBBHH',transaction,0,6,1,3,0,6))
        tid,protocol,length,unit=struct.unpack('>HHHB',receive(sock,7))
        if (tid,protocol,unit)!=(transaction,0,1) or not 2<=length<=254:raise ValueError('Invalid MBAP response')
        pdu=receive(sock,length-1)
        if pdu[0]&128:raise ValueError(f'Modbus exception {pdu[1]}')
        if len(pdu)!=14 or pdu[:2]!=bytes([3,12]):raise ValueError('Unexpected register payload')
        values=struct.unpack('>6H',pdu[2:])
        return dict(level_m=values[0]/10000,flow_m3_s=values[1]/1000000,sensor_mA=values[2]/1000,actuator_percent=values[3]/100,heartbeat=values[4],device_quality=values[5])
