print"test start"
import serial.tools.list_ports

ports=list(serial.tools.list_ports.comports())
if not ports:
   print"No ports found."
else:
  for port in ports:
    print"Hello World"
    print port.device
