#!/usr/bin/python

# https://realpython.com/intro-to-python-threading/


import socket
import logging
import threading
import time
import traceback
from LITECdefs import ControlModel
from labselect import labselect

import platform
if platform.system() == 'Windows':
    MSG_CONFIRM = 0
    MSG_WAITALL = 0
else:
    MSG_CONFIRM = socket.MSG_CONFIRM
    MSG_WAITALL = socket.MSG_WAITALL

LOG_LEVEL = logging.WARNING
LOG_FILE = 'simlog.log'

UDP_IP = '127.0.0.1'
UDP_PORT = 23500


LABEL_INT = 0x01
LABEL_GPIO = 0x02
LABEL_TIMERS = 0x03
LABEL_ADC1 = 0x04
LABEL_PCA0 = 0x05
LABEL_I2C = 0x06
LABEL_XBR = 0x07
LABEL_I2C_SENSORS = 0x10
LABEL_AUX = 0x30
LABEL_UPDATE_REQ = 0xF1
LABEL_UPDATE_DONE = 0xF2
LABEL_INIT = 0x5A
LABEL_ACK = 0xA5
LABEL_RESET = 0xFF

ctlmod = ControlModel()

logfile = logging.FileHandler('litecsim.log', mode='w')
logfile.setLevel(LOG_LEVEL)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s - %(message)s')
logfile.setFormatter(formatter)


class SimInterface():
    def __init__(self,controlmodel,runctl):
        self.s = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        self.s.bind((UDP_IP,UDP_PORT))
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.s.settimeout(0.1) # set timeout of socket to 100 ms
        self.ctlmod = controlmodel
        self.client = None
        self.runctl = runctl
        
        self.log = logging.getLogger('SVR')
        self.log.setLevel(LOG_LEVEL)
        self.log.addHandler(logfile)
        
        self.log.info("initialization complete")
    
    def exit(self):
        self.log.info("shutting down server")
        #self.s.shutdown(socket.SHUT_RDWR)
        self.s.close()
        
        
    def ctlupdate(self,label,buffer):
        #global ctlmod
        if label == LABEL_PCA0:
            self.log.debug("PCA0 Update received")
            self.ctlmod.pca0.update(buffer)
            self.log.debug("PCA0 Update applied")
            
        if label == LABEL_TIMERS:
            self.log.debug("TIMER Update received")
            self.ctlmod.timers01.update(buffer)
            self.log.debug("TIMER Update applied")
            
        elif label == LABEL_I2C_SENSORS:
            self.log.debug("I2C Sensors Update received")
            self.ctlmod.write2i2c(buffer)
            self.log.debug("I2C Sensors Update applied")
            
        elif label == LABEL_GPIO:
            self.log.debug("GPIO Update received")
            self.ctlmod.gpio.update(buffer)
            self.log.debug("GPIO Update applied")
        
        elif label == LABEL_XBR:
            self.log.debug("XBR Update received")
            self.ctlmod.xbr.update(buffer)
            self.log.debug("XBR Update applied")
            
        elif label == LABEL_ADC1:
            self.log.debug("ADC1 Update received")
            self.ctlmod.adc1.update(buffer)
            self.log.debug("ADC1 Update applied")

        elif label == LABEL_AUX:
            self.log.debug("AUX Update received")
            self.ctlmod.aux.update(buffer)
            self.log.debug("AUX Update applied")
            
        
    
    def ctldownload(self):
        self.log.info("State download requested")
        
        # send pca0 stuff
        buffer = bytearray([LABEL_PCA0]) + self.ctlmod.pca0.export()
        if not self.sendbuffer(buffer):
            return
        self.log.debug("PCA0 state sent")
        
        # send timer stuff
        buffer = bytearray([LABEL_TIMERS]) + self.ctlmod.timers01.export()
        if not self.sendbuffer(buffer):
            return
        self.log.debug("TIMER state sent")
        
        # send i2c stuff
        buffer = bytearray([LABEL_I2C_SENSORS])
        for sensor in self.ctlmod.i2csensors.values():
            buffer += bytearray([sensor.addr]) + sensor.read()
        if not self.sendbuffer(buffer):
            return
        self.log.debug("I2C sensor state sent")
        
        # send GPIO stuff
        buffer = bytearray([LABEL_GPIO]) + self.ctlmod.gpio.export()
        if not self.sendbuffer(buffer):
            return
        self.log.debug("GPIO state sent")
        
        # send ADC1 stuff
        buffer = bytearray([LABEL_ADC1]) + self.ctlmod.adc1.export()
        if not self.sendbuffer(buffer):
            return
        self.log.debug("ADC1 state sent")

        # send AUX stuff
        if self.ctlmod.aux.active:
            buffer = bytearray([LABEL_AUX]) + self.ctlmod.aux.export()
            if not self.sendbuffer(buffer):
                return
            self.log.debug("AUX state sent")
        
        
        # Send Done Flag
        buffer = bytearray([LABEL_UPDATE_DONE])
        if not self.sendbuffer(buffer):
            return
        self.log.info("State download complete")
        
    def sendbuffer(self,buffer):
        if self.client is None:
            return False
        try:
            self.log.debug("Socket send start")
            self.s.sendto(buffer,MSG_CONFIRM,self.client)
            self.log.debug("Socket send complete")
        except socket.error:
            self.log.info("CLIENT DISCONNECTED")
            self.client = None
            return False
        self.log.debug("Waiting for ACK")
        fail,buff,_ = self.receivebuffer()
        if fail:
            return
        self.log.debug("Received ACK")
        if buff[0] != LABEL_ACK:
            self.log.warning("Expected acknowledgement, got 0x{:02X}".format(buff[0]))
            pass
        return True
    
    def receivebuffer(self):
        try:
            buff,addr = self.s.recvfrom(1024,MSG_WAITALL)
            # Acknowledge anything buck an acknowledgement
            if buff[0] != LABEL_ACK:
                self.log.debug("Sending ACK")
                self.s.sendto(bytearray([LABEL_ACK]),MSG_CONFIRM,addr)
                self.log.debug("Sent ACK")
            if self.client is None:
                self.newclient(addr)
                return (True,buff,addr)
            else:
                return (False,buff,addr)
        except socket.timeout:
            if self.client is not None:
                self.log.info("CLIENT DISCONNECTED")
                self.client=None
            return (True,None,None)
        except ConnectionResetError:
            self.log.info("CLIENT DISCONNECTED: Connection Reset Error")
            self.client=None
            return (True,None,None)
            
    
    def newclient(self,addr):
        self.log.info("New client connected from PORT {}".format(addr[1]))
        self.client = addr
        
        
    def run(self):
        self.log.info("Server Running")
        reconnect_workaround = False
        while self.runctl > 0:
            if self.client is None:
                self.log.info("Waiting for connection ...")
            while self.client is None and self.runctl > 0:
                _,buff,addr = self.receivebuffer()
                if buff is None:
                    continue
                elif buff[0] == LABEL_INIT:
                    self.newclient(addr)
                else:
                    self.log.info("Received {} instead of LABEL_INIT. continuing anyway".format(buff[0]))
                    self.newclient(addr)
                    reconnect_workaround = True
                    
            
            while self.client and self.runctl > 0:
                if not reconnect_workaround:
                    self.log.debug("Waiting for Packet")
                    fail,buff,addr = self.receivebuffer()
                    self.log.debug("Received a Packet")
                else:
                    reconnect_workaround = False
                    fail = False
                        
                #self.log.info(buff)
                if not fail:
                    label = buff[0]
                    self.log.debug("Packet Received: label 0x{:02X}, length {}".format(label,len(buff)))
                    if label == LABEL_ACK:
                        self.log.warning("Ingoring stray ACK...")
                        continue
                    if label >= LABEL_INT and label <= LABEL_AUX:
                        self.ctlupdate(label, buff[1:])
                        pass
                    elif label == LABEL_UPDATE_REQ:
                        self.ctldownload()
                    elif label == LABEL_RESET:
                        self.ctlmod.reset()
                        if len(buff)>1:
                            if buff[1] > 2:
                                self.runctl.run = buff[1] # Convey the reset configuration
                            else:
                                self.runctl.run = 123   # Give a default config
                        else:
                            self.runctl.run = 2 # Plain reset
                            
                    else:
                        self.log.warning('Unknown label {} received'.format(label))
                        pass

# Make an object that can pass a kill signal                    
class ThreadCtl():
    def __init__(self):
        # 0:kill, 1:run, 2:reset (and run)
        self.run = 1
    
    def __eq__(self,other):
        return self.run == other
    
    def __lt__(self,other):
        return self.run < other
    
    def __gt__(self,other):
        return self.run > other
    
    def __le__(self,other):
        return self.run <= other
    
    def __ge__(self,other):
        return self.run >= other
    
    def kill(self):
        self.run = 0
    
#     def run(self):
#         return self.run

runctl = ThreadCtl()

def interface_func():
    server = SimInterface(ctlmod,runctl)
    try:
        server.run()
    except:
        server.log.exception('Simulation Errored:')
    finally:
        server.exit()
    runctl.kill()
    print("Sim Interface Killed")

def sim_func():
    #labselect(ctlmod,runctl,force_lab=5)
    labselect(ctlmod,runctl)
    runctl.kill()
    print("Simulation/GUI Killed")


    
    
if __name__== "__main__":
    
    sim_thread = threading.Thread(target=sim_func)
    interface_thread = threading.Thread(target=interface_func)
    
    
    sim_thread.start()
    interface_thread.start()
    
    while interface_thread.is_alive() and interface_thread.is_alive():
        time.sleep(1)
    
    print("Both Threads Killed, Quitting")
        
    
    
