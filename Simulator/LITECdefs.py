# This file stores the class define for the microcontroller and connected sensors
# This guy essentially stores and calculates functionality of the microcontroller
# It DOES NOT try to model the microcontroller instruction-perfect (not even close!!!)
import numpy as np
import os
from struct import pack,unpack,pack_into
import math

SYSCLK = 22.1184e6

SENSOR_REG_LENGTH = 50

class TIMERS01():
    def __init__(self):
        self.TCON = 0
        self.TMOD = 0
        self.CKCON = 0
        self.TMR0 = 0
        self.TMR1 = 0
    
        self.Noverflows_0 = 0
        self.Noverflows_1 = 0
        
        self.T0elapsed = 0
        self.T1elapsed = 0
        
        self.T0period = 0
        self.T1period = 0
        
        
    def reset(self):
        self.__init__()
    
    def update(self,packet):
        (self.TCON,self.TMOD,self.CKCON,self.TMR0,self.TMR1) = unpack('<BBBHH',packet)
        
        # Configs
        bitsizeref = [13,16,8,8]
        # Config Timer0
        # Get clock source
        t0clk = SYSCLK
        if not (self.CKCON & 0x08):
            t0clk = t0clk/12
        # get bit size
        t0bitsize = bitsizeref[self.TMOD & 0x03]
        maxcount = 0x10000
        if t0bitsize == 13:
            self.TMR0 = (self.TMR0 >> 3) | (self.TMR0 & 0x001F);   # Fix TMR0 for 13 bit
            maxcount = 0x2000
        elif t0bitsize == 8:
            self.TMR0 = self.TMR0 & 0x00FF   # Take only the low byte for 8 bit
            maxcount = 0x100
        Nperiod = maxcount - self.TMR0
        self.T0period = Nperiod/t0clk
        
        # Config Timer1
        # Get clock source
        t1clk = SYSCLK
        if not (self.CKCON & 0x10):
            t1clk = t1clk/12
        # get bit size
        t1bitsize = bitsizeref[(self.TMOD >> 4) & 0x03]
        maxcount = 0x10000
        if t1bitsize == 13:
            self.TMR1 = (self.TMR1 >> 3) | (self.TMR1 & 0x001F);   # Fix TMR0 for 13 bit
            maxcount = 0x2000
        elif t1bitsize == 8:
            self.TMR1 = self.TMR1 & 0x00FF   # Take only the low byte for 8 bit
            maxcount = 0x100
        Nperiod = maxcount - self.TMR1
        self.T1period = Nperiod/t1clk
        
    def export(self):
        output = pack('<HH',self.Noverflows_0,self.Noverflows_1)
        self.Noverflows_0 = 0   # Reset overflow counter when given to the program
        self.Noverflows_1 = 0
        return output
    
    def timestep(self,time_inc):
        if self.TCON & 0x10: # If timer is running...
            self.T0elapsed += time_inc
            self.Noverflows_0 = int(self.T0elapsed/self.T0period)
            self.T0elapsed = self.T0elapsed-self.T0period*self.Noverflows_0
        if self.TCON & 0x40: # If timer is running...
            self.T1elapsed += time_inc
            self.Noverflows_1 = int(self.T1elapsed/self.T1period)
            self.T1elapsed = self.T1elapsed-self.T1period*self.Noverflows_1
            
        
        
        

class PCA0():
    def __init__(self):
        self.PCA0CN = 0
        self.PCA0MD = 0
        self.PCA0 = 0;
        self.PCA0CPn = [0,0,0,0,0]
        self.PCA0CPMn = [0,0,0,0,0]
        self.Noverflows = 0
        
        self.clksrc = 0
        self.Tperiod = 0
        self.Tpw = [0,0,0,0,0]
        self.DC = [0,0,0,0,0]
        
        self.Telapsed = 0
        self.unhandledInt = False   # Keep track weather a triggered interrupt has been sent
                                    # Used to fix getting "out of sync" where the interrupt
                                    # might be cleared before sent to client
                                    
    def reset(self):
        self.__init__()
    
    def update(self,packet):
        unpacked = unpack('<BBHBBBBBHHHHH',packet)
        # Only allow overwrite of CF if it has been handled
        if self.unhandledInt:
            self.PCA0CN &= 0x80
            self.PCA0CN |= unpacked[0] & ~0x80
        else:
            self.PCA0CN = unpacked[0]
        self.PCA0MD = unpacked[1]
        self.PCA0 = unpacked[2]
        self.PCA0CPMn = unpacked[3:8]
        self.PCA0CPn = unpacked[8:13]
        
        # Determine clock source
        pca0clkdict = {0:SYSCLK/12,1:SYSCLK/4,4:SYSCLK}
        self.clksrc = pca0clkdict.get((self.PCA0MD>>1)&0x07,0)
        # Calculate period
        Nperiod = 0x10000
        # If overflow interrupt is active, use PCA0 value as starting point
        if self.PCA0MD & 0x01:
            Nperiod -= self.PCA0
        if self.clksrc == 0:
            self.Tperiod = 1e6 # Some large number
        else:
            self.Tperiod = Nperiod/self.clksrc
        # Calculate pulsewidths. Only update if PWM16 is enables (forget rest of functionality)
        for i in range(5):
            if(self.PCA0CPMn[i] == 0xC2):
                Npw = 0xFFFF-self.PCA0CPn[i]
                if Npw > Nperiod:
                    Npw = 0
                if self.clksrc == 0:
                    self.Tpw[i] = 0
                    self.DC[i] = 0
                else:
                    self.Tpw[i] = Npw/self.clksrc
                    self.DC[i] = self.Tpw[i]/self.Tperiod
                
    def export(self):
        self.unhandledInt = False
        output = pack('<BH',self.PCA0CN,self.Noverflows)
        self.Noverflows = 0 # Reset overflow counter when sent to program
        return output
        
    def timestep(self,time_inc):
        if not self.PCA0CN & 0x40:  # If the PCA is not running, don't increment the time step
            return 0
        self.Telapsed += time_inc
        if self.Telapsed >= self.Tperiod:
            self.Noverflows = int(self.Telapsed/self.Tperiod)
            self.unhandledInt = True
            self.Telapsed = self.Telapsed-self.Tperiod*self.Noverflows
            self.PCA0CN |= 0x80     # Set CF
    
    def getPW(self,ccmnum):
        if ccmnum >= 0 and ccmnum <= 4:
            return self.Tpw[ccmnum]
        else:
            return 0
        
# This class is probably not necessary (handled by C8051_SIM.h)
class Interrupts():
    def __init__(self):
        self.IE = 0;
        self.EIE1 = 0;
        
        self.pca0en = 0;
        self.timeren = [0,0,0,0,0]
    
    def reset(self):
        self.__init__()
        
    def update(self,packet):
        (self.IE,self.EIE1) = unpack('<BB',packet)
        if self.IE & 0x80:
            self.pca0en = int((self.EIE1 & 0x08)>0)
            self.timeren[0] = int((self.IE & 0x02)>0)
            self.timeren[1] = int((self.IE & 0x08)>0)
            self.timeren[2] = int((self.IE & 0x20)>0)
        else:
            self.pca0en = 0
            self.timeren = [0,0,0,0,0]

class AUXdata():
    def __init__(self):
        self.active = False
        self.data_in = []
        self.data_out = [0]*10
        self.in_buffer = 0

    def reset(self):
        self.__init__()

    def update(self,packet):
        self.active = True
        if self.in_buffer < 10:
            self.in_buffer += 1
            self.data_in.append(list(unpack('<BBBBBBBBBB',packet)))

    def get_next(self):
        next = False
        if self.in_buffer:
            self.in_buffer -= 1
            next = self.data_in[0]
            self.data_in = self.data_in[1:]
        return next

    def export(self):
        return pack('<BBBBBBBBBB',*self.data_out)


class SMBus():
    def __init__(self):
        self.SMB0CR = 0
        self.ENSMB = 0
        
        self.active = 0
        
    def reset(self):
        self.__init__()
        
    def update(self,packet):
        (self.SMB0CR,self.ENSMB) = unpack('<BB',packet)
        if self.SMB0CR == 0x93 and self.ENSMB:
            self.active = 1

class SMBSensor():
    def __init__(self,addr,name):
        self.addr = addr
        self.name = name
        self.writeregs = bytearray(SENSOR_REG_LENGTH)    # Values written into by program
        self.readregs = bytearray(b'\xff')*50   # Values given to program (i2c read)
        self.available = True   # mark whether the device can be accessed (e.g., Ranger during ping)
    
    def write(self,startreg,values):
        startreg = startreg & 0x7F  # Clear the MSB - In support of the Accelerometer
        accessreg = startreg
        if not self.available:
            return
        for value in values:
            if accessreg >= SENSOR_REG_LENGTH:
                break
            self.writeregs[accessreg] = value
            accessreg += 1
        self.actionwrite(startreg,values)
    
    def read(self):
        if not self.available:
            return bytearray(b'\xff')*50
        return self.readregs
    
    def actionwrite(self,startreg=None,values=None):
        pass
    
    def timestep(self,timeinc):
        pass
    
class Ranger(SMBSensor):
    def __init__(self):
        super(Ranger,self).__init__(0xE0,"ranger")
        
        self.ping_active = False
        self.Telapsed = 0
        self.light = 0
        self.echo1 = 500    # set to match simulation
        self.echo2 = 1000
        self.echo3 = 1500
        
    def reset(self):
        addr = self.addr
        self.__init__()
        self.addr = addr
    
    def actionwrite(self,startreg=None,values=None):
        if   self.writeregs[0] == 0x50:
            self.ping_active = 'in'
            self.writeregs[0] = 0
        elif self.writeregs[0] == 0x51:
            self.ping_active = 'cm'
            self.writeregs[0] = 0
        elif self.writeregs[0] == 0x52:
            self.ping_active = 'us'
            self.writeregs[0] = 0
        if self.ping_active:
            self.available = False
            self.Telapsed = 0
            
    def timestep(self,timeinc):
        if not self.ping_active:
            return
        self.Telapsed += timeinc
        if self.Telapsed >= 0.065:       # 65 milliseconds has passed
            self.Telapsed = 0
            self.ping_active = False
            self.available = True
            #pack_into('>BHHH',self.readregs,1,self.light,self.echo1,self.echo2,self.echo3)
            pack_into('>BBHHH',self.readregs,0,0x13,self.light,self.echo1,self.echo2,self.echo3)
    
    # by default, the echo values given should be in cm.    
    def setecho(self,echo1cm,echo2cm=None,echo3cm=None):
        if echo2cm is None:
            echo2cm = echo1cm*2
        if echo3cm is None:
            echo3cm = echo1cm*3
        if self.ping_active == 'in':
            self.echo1 = echo1cm/2.54
            self.echo2 = echo2cm/2.54
            self.echo3 = echo3cm/2.54
        elif self.ping_active == 'us':
            self.echo1 = echo1cm/34300  # Assuming 343 m/s
            self.echo2 = echo1cm/34300
            self.echo3 = echo1cm/34300
        elif self.ping_active == 'cm':
            self.echo1 = echo1cm
            self.echo2 = echo2cm
            self.echo3 = echo3cm
        else:
            return
        self.echo1 = int(self.echo1)
        self.echo2 = int(self.echo2)
        self.echo3 = int(self.echo3)
        if self.echo1 > 0xFFFF:
            self.echo1 = 0xFFFF
        elif self.echo1 < 0:
            self.echo1 = 0
        if self.echo2 > 0xFFFF:
            self.echo2 = 0xFFFF
        elif self.echo2 < 0:
            self.echo2 = 0
        if self.echo3 > 0xFFFF:
            self.echo3 = 0xFFFF
        elif self.echo3 < 0:
            self.echo3 = 0
            
    def setlight(self,lightval):
        if self.ping_active:
            self.light = int(lightval)
        if self.light > 0xFF:
            self.light = 0xFF
        elif self.light <0:
            self.light = 0
            
class Compass(SMBSensor):
    def __init__(self):
        super(Compass,self).__init__(0xC0,'compass')
        
        self.Telapsed = 0
        self.readregs[0] = 42  # set firmware revision number
        self.direction = 0
        
    def reset(self):
        addr = self.addr
        self.__init__()
        self.addr = addr
        
    def setdirection(self,direction):   # Direction is in radians
        self.direction = direction % (2*np.pi)
        #if self.addr == 0x42:
        
    def timestep(self,timeinc):
        self.Telapsed += timeinc
        if self.Telapsed >= 0.033:
            self.Telapsed = 0
            smalldir = int(self.direction/(2*np.pi)*256)
            largedir = int(self.direction/(2*np.pi)*3600)
            pack_into('>BH',self.readregs,1,smalldir,largedir)
            self.readregs[4:12] = bytearray(os.urandom(8))

class Accelerometer(SMBSensor):
    def __init__(self):
        super(Accelerometer,self).__init__(0x3A,'accelerometer')
        self.active = False
        self.x_accel = 0
        self.y_accel = 0
        self.z_accel = 0
        self.Telapsed = 0
        
    def reset(self):
        self.__init__()
        
    def actionwrite(self,startreg=None,values=None):
        for reg,value in enumerate(values,start=startreg):
            if reg == 0x20 and value == 0x6B:   # Turn on from Accel_Init_C() (Not handing other turn on cases)
                self.active = True
            elif reg == 0x27:
                self.readregs[0x27] &= value    # Clear any status bits marked
        
    def timestep(self,timeinc):
        self.Telapsed += timeinc
        if self.Telapsed >= 0.01:
            self.Telapsed = 0
            if self.readregs[0x27] | 0x0F:
                self.readregs[0x27] |= (self.readregs[0x27] << 4) & 0xF0   # Mark overruns
            self.readregs[0x27] |= 0x0F # Mark new data ready
            pack_into('<hhh',self.readregs,0x28,self.x_accel,self.y_accel,self.z_accel)
            
    def setaccel(self,x_accel=None,y_accel=None,z_accel=None):
        if x_accel:
            self.x_accel = self.setlimits(int(x_accel/.061)) # Scale to 16-bits
        if y_accel:
            self.y_accel = self.setlimits(int(y_accel/.061))
        if z_accel:
            self.z_accel = self.setlimits(int(z_accel/.061))
        #print('{}\t{}\t{}'.format(x_accel,y_accel,z_accel))
    
    def setlimits(self,accel):
        if abs(accel > 0x7FFF):
            accel = math.copysign(0x7FFF,accel)
        return accel
    
class Actuator(SMBSensor):
    def __init__(self):
        super(Actuator,self).__init__(0x42,'actuator')
        self.ID = 0x01
        self.rev = 0x60
        self.status = False
        self.speed = 0
        self.direction = 0
        self.Telapsed = 0
        self.Telapsed_d = 0
        pack_into('>B',self.readregs,1,self.rev)
        
    def timestep(self,timeinc):
        self.Telapsed_d += timeinc
        if self.status and self.Telapsed_d >= 0.1:
            self.status = False
        self.Telapsed += timeinc
        if self.Telapsed >= 0.03:
            pack_into('>BB',self.readregs,0x02,self.speed,self.direction)
            self.Telapsed -= 0.03
        
        
    def reset(self):
        ID = self.ID
        self.__init__()
        self.ID = ID
        
    def actionwrite(self,startreg=None,values=None):
        self.ID = self.writeregs[0]
        if self.writeregs[1] < 0x02:
            self.status = self.writeregs[1]
            self.Telapsed_d = 0
        pack_into('>B',self.readregs,0,self.ID)
        
    
class GPIO():
    def __init__(self):
        self.data = [0,0,0,0]
        self.mdout = [0,0,0,0]
        self.mdin = [0,0xFF,0,0]
        self.mdin_changed = False
        
    def update(self,packet):
        unpacked = unpack('<BBBBBBBBBBBB',packet)
        self.data = list(unpacked[0::3])
        self.mdout = list(unpacked[1::3])
        mdin = list(unpacked[2::3])
        if self.mdin[1] != mdin[1]:
            self.mdin_changed = True
            self.mdin[1] = mdin[1]
        
    def export(self):
        return pack('<BBBB',*self.data)
        
    def reset(self):
        self.__init__()
        
    def getport_out(self,port):
        return self.data[port] & self.mdout[port]
        
    def getpin(self,port,pin):
        return bool(self.data[port] & (0x01 << pin))
    
    def setpin(self,port,pin,val):
        if val:
            self.data[port] |= 0x01 << pin
        else:
            self.data[port] &= ~(0x01 << pin)
    
    def ispinoutput(self,port,pin):
        return bool(self.mdout[port] & (0x01 << pin))
            
    
class XBR():
    def __init__(self,pca0,gpio,adc1):
        self.XBR0 = 0
        self.XBR1 = 0
        self.XBR2 = 0
        self.pins = []
        self.pca0 = pca0
        self.gpio = gpio
        self.adc = adc1
        self.reset()
        
    def update(self,packet):
        (XBR0n,XBR1n,XBR2n) = unpack('<BBB',packet)
        if XBR0n != self.XBR0 or XBR1n != self.XBR1 or XBR2n != self.XBR2:
            self.XBR0 = XBR0n
            self.XBR1 = XBR1n
            self.XBR2 = XBR2n
            self.updatePins()
        if self.gpio.mdin_changed:
            self.gpio.mdin_changed = False
            self.updatePins()
    
    def updatePins(self):
            
        nextpin=0
        if self.XBR0 & 0x04:
            self.pins[int(nextpin/8)][nextpin%8] = 'TX0'
            nextpin += 1
            self.pins[int(nextpin/8)][nextpin%8] = 'RX0'
            nextpin += 1
        if self.XBR0 & 0x02:
            self.pins[int(nextpin/8)][nextpin%8] = 'SCK'
            nextpin += 1
            self.pins[int(nextpin/8)][nextpin%8] = 'MISO'
            nextpin += 1
            self.pins[int(nextpin/8)][nextpin%8] = 'MOSI'
            nextpin += 1
            self.pins[int(nextpin/8)][nextpin%8] = 'NSS'
            nextpin += 1
        if self.XBR0 & 0x01:
            self.pins[int(nextpin/8)][nextpin%8] = 'SDA'
            nextpin += 1
            self.pins[int(nextpin/8)][nextpin%8] = 'SCL'
            nextpin += 1
        if self.XBR2 & 0x04:
            nextpin += self.assignAnalog(nextpin)
            self.pins[int(nextpin/8)][nextpin%8] = 'TX1'
            nextpin += 1
            nextpin += self.assignAnalog(nextpin)
            self.pins[int(nextpin/8)][nextpin%8] = 'RX1'
            nextpin += 1
        for i in range(min((self.XBR0>>3)&0x07,5)):
            if self.assignAnalog(nextpin):
                nextpin += 1
                continue
            self.pins[int(nextpin/8)][nextpin%8] = 'CCM{}'.format(i)
            nextpin += 1
        while nextpin < 32:
            if self.assignAnalog(nextpin):
                nextpin += 1
                continue
            self.pins[int(nextpin/8)][nextpin%8] = 'GPIO'
            nextpin += 1
        # TODO: Implement Analog inputs
    
    def assignAnalog(self,nextpin):
        if int(nextpin/8) == 1: # If on port 1
            if (~self.gpio.mdin[1]) & (1 << (nextpin % 8)): # Check if analog mode is active
                self.pins[int(nextpin/8)][nextpin%8] = 'ADC'
                return 1
        return 0
            
            
    def getpin(self,port,pin,signal=None):
        if signal is None:
            return self.pins[port][pin]
        else:
            pintype = self.pins[port][pin]
            if signal == 'CCM':
                if pintype.startswith(signal):
                    if self.gpio.ispinoutput(port,pin):
                        return self.pca0.DC[int(self.pins[port][pin][-1])]
                    else:
                        return 0
                elif pintype == 'GPIO':
                    return self.gpio.getpin(port,pin)
                else:
                    return 0
            elif signal == 'GPIO' and pintype == 'GPIO':
                return self.gpio.getpin(port,pin)
            else:
                return 0
            
    def setpin(self,port,pin,value):
        if self.pins[port][pin] == 'GPIO':
            if value < 1:   # In Case a voltage is given here, assume threshold is 1V
                self.gpio.setpin(port, pin, False)
            else:
                self.gpio.setpin(port, pin, True)
        elif self.pins[port][pin] == 'ADC':
            self.adc.setvoltage(value,pin)
                
    def reset(self):
        self.XBR0 = 0
        self.XBR1 = 0
        self.XBR2 = 0x40
        self.pins = [['GPI0' for _ in range(8)] for _ in range(4)]
        self.pins[0][0] = 'tx0'
        self.pins[0][1] = 'rx0'
        self.updatePins()
        
class ADC1():
    def __init__(self):
        self.REF0CN = 0
        self.ADC1CF = 0xF8
        self.ADC1CN = 0
        self.AMX1SL = 0
        self.gain = 0.5
        self.result = 0
        self.active = False
        self.active_cooldown = False # Cannot start if this is True
        
    def reset(self):
        self.__init__()
        
    def update(self,packet):
        (self.REF0CN,self.ADC1CF,self.ADC1CN,self.AMX1SL) = unpack('<BBBB',packet)
        self.gain = self.ADC1CF & 0x03
        if self.gain == 0:
            self.gain = 0.5
        elif self.gain == 3:
            self.gain = 4
        if (not self.active) and (not self.active_cooldown):
            if (self.ADC1CN & 0x9F) == 0x90:
                self.active = 1
                self.active_cooldown = True
                self.result = 0
        if (not self.active) and (self.active_cooldown):
            if not (self.ADC1CN & 0x10):
                self.active_cooldown = False
                
    def setvoltage(self,voltage,pin):
        if (pin == self.AMX1SL) and self.active:
            self.result = int(256*self.gain*voltage/2.4)
            if self.result < 0:
                self.result = 0
            elif self.result >255:
                self.result = 255

    def timestep(self,step):
        # Lock in ADC and deactivate
        if self.active:
            self.active = False
            self.ADC1CN = 0xA0  # Mark flags for ADC complete
        
    def export(self):
        if self.active:
            return pack('<BB',0x01,self.result)
        elif self.active_cooldown:
            self.ADC1CN = 0xA0
            return pack('<BB',0x02,self.result)
        return pack('<BB',0,self.result)
    
class ControlModel():
    def __init__(self):
        self.pca0 = PCA0()
        self.timers01 = TIMERS01()
        self.ints = Interrupts()
        self.i2c = SMBus()
        self.gpio = GPIO()
        self.adc1 = ADC1()
        self.aux = AUXdata()
        self.xbr = XBR(self.pca0,self.gpio,self.adc1)
        self.i2csensors = {}
        self.ranger = Ranger()
        self.i2csensors.update({self.ranger.addr:self.ranger})
        self.compass = Compass()
        self.i2csensors.update({self.compass.addr:self.compass})
        self.compass2 = Compass()   # Used for lab 6 F20
        self.compass2.addr = 0x42
        self.i2csensors.update({self.compass2.addr:self.compass2})
        #self.accel = Accelerometer()
        #self.i2csensors.update({self.accel.addr:self.accel})
        #self.actuator = Actuator()
        #self.i2csensors.update({self.actuator.addr:self.actuator})
    
    def timestep(self,timeinc):
        self.pca0.timestep(timeinc)
        self.timers01.timestep(timeinc)
        self.ranger.timestep(timeinc)
        self.compass.timestep(timeinc)
        self.compass2.timestep(timeinc)
        #self.accel.timestep(timeinc)
        self.adc1.timestep(timeinc)
        #self.actuator.timestep(timeinc)
        
    def write2i2c(self,buffer):
        target = self.i2csensors.get(buffer[0],False)
        if target:
            target.write(buffer[1],buffer[2:])
            
    def reset(self):
        self.pca0.reset()
        self.timers01.reset()
        self.ints.reset()
        self.i2c.reset()
        for sensor in self.i2csensors.values():
            sensor.reset()
        self.xbr.reset()
        self.gpio.reset()
        self.adc1.reset()
        self.aux.reset()
        
