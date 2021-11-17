import pygame
import math
from pygments.lexers import ampl, int_fiction
import numpy as np

def scaleImage(image,scale):
    if scale != 1:
        rect = image.get_rect()
        image = pygame.transform.smoothscale(image, tuple((np.array(rect.size)*scale).astype(int)))
    return (image,image.get_rect())

def scaleCoord(coord,scale):
    return (np.array(coord)*scale).astype(int)

class ButtonBox():
    def __init__(self):
        self.text = None
        self.text_offset = np.array([0,0])
        self.rect = None
        self.hit = False
        self.color = (165,165,165)
        self.colordown = (255,255,255)
        self.ico = None
        self.ico_offset = np.array([0,0])
        self.func = lambda x:None
        
    def draw(self,surf):
        if self.hit:
            pygame.draw.rect(surf,self.colordown,self.rect)
        else:
            pygame.draw.rect(surf,self.color,self.rect)
        if self.text is not None:
            surf.blit(self.text,self.text.get_rect(center=tuple((np.array(self.rect.center)+self.text_offset).astype(int))))
        if self.ico is not None:
            surf.blit(self.ico,self.ico.get_rect(center=tuple((np.array(self.rect.center)+self.ico_offset).astype(int))))
        
class DrivingCar():
    def __init__(self,asset_path,scale=1,center=(0,0),angle=0,simstep=0.01,png=True):
        # Initialize car
        if not png:
            self.text.get_rect(center=tuple((np.array(self.rect.center)+self.text_offset).astype(int)))
            self.car = pygame.image.load(asset_path+"Car/carfull_nowheels_cent.jpg").convert()
            (self.car,self.rect_car) = scaleImage(self.car,scale)
        else:
            self.car = pygame.image.load(asset_path+"Car/carfull_nowheels_cent.png").convert_alpha()
            (self.car,self.rect_car) = scaleImage(self.car,scale*4)
        
        # Initialize wheels
        self.wheel = pygame.image.load(asset_path+"Car/singlewheel.png").convert_alpha()
        (self.wheel,self.rect_wheel) = scaleImage(self.wheel,scale*1.4)
        self.rect_Lwheel = self.rect_wheel.copy()
        self.rect_Rwheel = self.rect_wheel.copy()
        self.surfsize = (self.rect_car.width+2*self.rect_wheel.height,
                                    self.rect_car.height+self.rect_wheel.height)
        self.rect = self.rect_car.copy()
        
        self.rect_car.center = tuple((np.array(self.surfsize)/2).astype(int))
        self.rect_Lwheel.center = (int(self.rect_car.left+120*scale),
                                   int(self.rect_car.top+180*scale))
        self.rect_Rwheel.center = (int(self.rect_car.right-145*scale),
                                   int(self.rect_car.top+180*scale))
        
        self.angle_orig = np.radians(angle)
        self.angle = np.radians(angle)  # Radians
        
        self.pos_x_orig = center[0]
        self.pos_y_orig = center[1] 
        
    
        self.simstep = simstep
        self.Servo = Servo(simstep)
        self.Drive = Drive(simstep)
        
        # Poor drive friction implementation
        self.start_speed = 0.1*self.Drive.maxspeed    # Minimum speed at which the car needs to start
        self.dead_speed = 0.05*self.Drive.maxspeed      # Speed at which car will not cease to move
        
        # Tilt effects
        self.pitch = 0
        self.roll = 0
        
        self.pitch_active = True 
        
        # Forward facing ranger
        self.r_vec = np.array([0,-self.rect_car.height/2])
        self.r_beam = np.radians(60)/2
        self.r_dist = 500
        
        self.t_angle = 0    # Angle at which the obstacle is detected
        
        # Crude acceleration of car
        self.last_speed = 0
        self.accel = 0
        
        self.reset()
        
    def reset(self):
        self.angle = self.angle_orig  # Radians
        self.pos_x = self.pos_x_orig
        self.pos_y = self.pos_y_orig
        self.Servo.reset()
        self.Drive.reset()
        self.rect.center = (10000,100000)  # Move the car to an empty area so we don't collide immediately      
        self.last_speed = 0
        
    def draw(self,screen):
        #rotate wheels
        rot_wheel = pygame.transform.rotate(self.wheel,self.Servo.angle)
        rot_rect_Lwheel = rot_wheel.get_rect()
        rot_rect_Lwheel.center = self.rect_Lwheel.center
        rot_rect_Rwheel = rot_wheel.get_rect()
        rot_rect_Rwheel.center = self.rect_Rwheel.center
        
        surf = pygame.Surface(self.surfsize,pygame.SRCALPHA)
        surf.blit(self.car,self.rect_car)
        surf.blit(rot_wheel,rot_rect_Lwheel)
        surf.blit(rot_wheel,rot_rect_Rwheel)
        surf = pygame.transform.rotate(surf,math.degrees(self.angle))
        #self.rect = surf.get_rect(center=(self.pos_x,self.pos_y))
        #self.rect = self.rect_car.copy()
        self.rect = pygame.Rect(0,0,
                                int(max(abs(self.rect_car.height*np.sin(self.angle)),abs(self.rect_car.width*np.cos(self.angle)))),
                                int(max(abs(self.rect_car.height*np.cos(self.angle)),abs(self.rect_car.width*np.sin(self.angle))))
                                )
        self.rect.center=self.center()
        #pygame.draw.rect(screen,[0,0,0],self.rect,width=2)
        screen.blit(surf,surf.get_rect(center=(self.pos_x,self.pos_y)))
        
    # Equations from Polack et.al., 2017 "The kinematic bicycle model:..."
    def update(self):
        self.Servo.update()
        self.Drive.update()
        c1 = np.arctan(0.5*np.tan(np.radians(self.Servo.angle)))
        
        speed = self.calcspeed()
                     
        self.angle += speed*self.simstep*np.sin(c1)/12
        self.angle = self.angle % (2*np.pi)
        #self.pos_x += self.Drive.speed*np.cos(np.radians(self.Servo.angle)+c1)*self.simstep
        #self.pos_y += self.Drive.speed*np.sin(np.radians(self.Servo.angle)+c1)*self.simstep
        self.pos_y -= speed*np.cos(self.angle+c1)*self.simstep
        self.pos_x -= speed*np.sin(self.angle+c1)*self.simstep
        
        self.accel = (speed-self.last_speed)/self.simstep # speed is px/s here, so accel is px/s^2
        self.accel = self.accel*0.24/self.rect_car.height*.7 # convert px/s to m/s: 
                                                        # car is 24 cm long front axle to back axle
                                                        # car is ~ rectangle height*0.7 px from axle to axle   
        self.last_speed = speed # store last speed
        #print('{}\t{}'.format(speed,self.accel))
        
    def calcspeed(self):
        # Pitch dependent speed
        speed = self.Drive.speed*(1-self.pitch/4)
        
        # if speed is zero, leave it at 0!
        if speed == 0:
            return 0
        
        # Also don't change the speed if we are driving downhill
        if speed > 0 == self.pitch < 0:
            return speed
            
        # If we've gotten here, we're driving uphill (or on level ground)
        # If we're stopped and trying to start, we need to be trying to going faster than dead_speed
        if self.last_speed == 0:
            if abs(speed) <= self.start_speed:
                return 0    # Not enough force, don't move
            else:
                return speed # Enough force, start moving
        
        # If we've gotten here, we're moving and going uphill
        # Check if we're going to slow
        if abs(speed) < self.dead_speed:
            return 0
        else:
            return speed
        
    def center(self):
        return np.array((self.pos_x,self.pos_y))
    
    def setcenter(self,newcenter):
        (self.pos_x,self.pos_y) = newcenter
    
    def centerorig(self):
        return np.array((self.pos_x_orig,self.pos_y_orig))
    
    def detectobstacle(self):
#         anglesin = np.sin(self.angle)
#         anglecos = np.cos(self.angle)
#         txmatrix = np.array([[anglecos,anglesin],[-anglesin,anglecos]])
#         r_vec = txmatrix.dot(self.r_vec)
#         r_pos = r_vec + np.array(self.center())
#         
#         r_to_o = np.array(target)-r_pos
#         dist = np.linalg.norm(r_to_o)-radius
#         angle = np.arccos(r_vec.dot(r_to_o)/(np.linalg.norm(r_vec)*np.linalg.norm(r_to_o)))
#         if abs(angle) <= self.r_beam and dist < 490:
#             return int(dist)#+np.random.normal(0,scale=3))
#         return int(np.random.normal(500,scale=10))
        return self.r_dist # Calculated in collidecirc
    
    def collidecirc(self,target=(0,0),radius=10):
    
        #rotate circle around car (so car is straight up and down)
        anglesin = np.sin(-self.angle)
        anglecos = np.cos(-self.angle)
        txmatrix = np.array([[anglecos,anglesin],[-anglesin,anglecos]])
        c_to_o = txmatrix.dot(np.array(target)-np.array(self.center()))
        r_to_o = c_to_o - self.r_vec
        dist = np.linalg.norm(r_to_o)-radius
        angle = np.arccos(self.r_vec.dot(r_to_o)/(np.linalg.norm(self.r_vec)*np.linalg.norm(r_to_o)))
        if abs(angle) <= self.r_beam and dist <1500 and dist > 50:# and dist < 490:
            self.r_dist = int(dist)#+np.random.normal(0,scale=3))
        elif abs(angle) < np.radians(90) and dist < 50:# and dist < 490:
            self.r_dist = int(dist)
        else:
            self.r_dist = int(np.random.normal(1550,scale=10))
        # https://stackoverflow.com/questions/24727773/detecting-rectangle-collision-with-a-circle
        
        # get heading
        self.t_angle = math.atan2(c_to_o[0],-c_to_o[1])
        
        
        w = self.rect_car.width/2
        h = self.rect_car.height/2
        cleft,ctop = c_to_o[0]-radius,c_to_o[1]-radius
        cright,cbot = c_to_o[0]+radius,c_to_o[1]+radius
        
        
        # reject if bounding boxes do not intersect
        if not (w < cleft or -w > cright or h < ctop or -h > cbot):
            # Detect if circle hits a corner
            for _x in (-w,w):
                for _y in (-h,h):
                    if math.hypot(_x-c_to_o[0],_y-c_to_o[1]) <= radius:
                        return True
            # Detect if circle hits top or bottom
            if c_to_o[0] < w and c_to_o[0] > -w:
                if -h < cbot and h > ctop:
                    return True
            # Detect if circle hits left or right
            if c_to_o[1] < h and c_to_o[1] > -h:
                if w > cleft and -w < cright:
                    return True
                    
        return False
    
    def getangle(self):
        return -self.angle+np.radians(np.random.normal(0,scale=5))        

        
class Slider():
    def __init__(self,image='',val='',output=(0,100),center=(0,0),size=100,axis=0,scale=1):
        self.val = 0
        self.output = output # Minimum/Maximum output values
        self.axis = axis
        self.center = center
        self.pos = center
        self.hit = False
        
        if scale != 1:
            self.center = (np.array(self.center)*scale).astype(int)
            self.pos = (np.array(self.pos)*scale).astype(int)
            size = int(size*scale)
        
        self.limits = [int(self.pos[self.axis]-size/2),int(self.pos[self.axis]+size/2)]
        
        self.interp_coeff = (self.output[1]-self.output[0])/size
        
        if isinstance(image,str):
            self.image = pygame.image.load(image).convert()
            #self.image = pygame.transform.scale(self.image,(int(387*.4),int(500*.4)))
        else:
            self.image = image
        
        self.image,self.image_rect = scaleImage(self.image,scale)
        self.image_rect.center = self.pos
        
        if not val:
            val = self.limits[0]
        else:
            self.setval(val)
        
    def draw(self,screen):
        screen.blit(self.image,self.image_rect)
        
    def move(self,pos=''):
        if pos == '':
            pos = pygame.mouse.get_pos()
        new_center = pos[self.axis]
        if new_center < self.limits[0]:
            new_center = self.limits[0]
        elif new_center > self.limits[1]:
            new_center = self.limits[1]
        if self.axis:    # True if axis is vert, False if horiz
           self.image_rect.centery = new_center
        else:
            self.image_rect.centerx = new_center
        self.val = self.interp_coeff*(new_center - self.limits[0])
    
    def setval(self,val):
        self.val = val
        if self.val > self.output[1]:
            self.val = self.output[1]
        elif self.val < self.output[0]:
            self.val = self.output[0]
        new_center = int((self.val-self.output[0])/self.interp_coeff)+self.limits[0]
        if self.axis:    # True if axis is vert, False if horiz
           self.image_rect.centery = new_center
        else:
            self.image_rect.centerx = new_center
            
    def getratio(self):
        return self.val/(self.output[1]-self.output[0])
    
    def checkClick(self,pos):
        return self.image_rect.collidepoint(pos)

class SlideSwitch():
    def __init__(self,file,val,center=(0,0),scale=1,axis='y',labels=True,title='',port=None,pin=None):
        self.axis = axis
        self.val_orig = val
        self.val = val
        self.image = pygame.image.load(file).convert_alpha()
        self.rect = self.image.get_rect()
        self.image = pygame.transform.smoothscale(self.image,(int(self.rect.width*scale),int(self.rect.height*scale)))
        if axis == 'x':
            self.image = pygame.transform.rotate(self.image,-90)
        self.rect = self.image.get_rect()
        self.rect.center = center
        self.labels = labels
        self.title = False
        self.port = port
        self.pin = pin
        font = pygame.font.SysFont('Serif', 18)
        
        if labels:
            self.label0 = font.render('0',True,(0,0,0))
            self.label0_rect = self.label0.get_rect()
            self.label0 = pygame.transform.smoothscale(self.label0,(int(self.label0_rect.width*scale),int(self.label0_rect.height*scale)))
            self.label0_rect = self.label0.get_rect()
            
            self.label1 = font.render('1',True,(0,0,0))
            self.label1_rect = self.label1.get_rect()
            self.label1 = pygame.transform.smoothscale(self.label1,(int(self.label1_rect.width*scale),int(self.label1_rect.height*scale)))
            self.label1_rect = self.label1.get_rect()
            
            if axis == 'y':
                self.label0_rect.centerx = self.rect.centerx
                self.label0_rect.centery = self.rect.centery + 35*scale
                self.label1_rect.centerx = self.rect.centerx
                self.label1_rect.centery = self.rect.centery - 37*scale
            else:
                self.label0_rect.centery = self.rect.centery
                self.label0_rect.centerx = self.rect.centerx - 37*scale
                self.label1_rect.centery = self.rect.centery
                self.label1_rect.centerx = self.rect.centerx + 37*scale
        if title or (self.port is not None and self.pin is not None):
            if not title:
                title = 'P{}.{}'.format(self.port,self.pin)
            self.title = font.render(title,True,(0,0,0))
            self.title_rect = self.title.get_rect()
            self.title = pygame.transform.smoothscale(self.title,(int(self.title_rect.width*scale),int(self.title_rect.height*scale)))
            self.title_rect = self.title.get_rect()
            if axis == 'y':
                self.title_rect.centerx = self.rect.centerx
                self.title_rect.bottom = self.rect.top - 5
            else:
                self.title_rect.right = self.rect.left - 5
                self.title_rect.centery = self.rect.centery
                
    def adjustcenter(self,center=(0,0)):
        dx = center[0]-self.rect.centerx
        dy = center[1]-self.rect.centery
        
        self.rect.centerx = self.rect.centerx+dx
        self.rect.centery = self.rect.centery+dy
        self.label0_rect.centerx = self.label0_rect.centerx+dx
        self.label0_rect.centery = self.label0_rect.centery+dy
        self.label1_rect.centerx = self.label1_rect.centerx+dx
        self.label1_rect.centery = self.label1_rect.centery+dy
        self.title_rect.centerx = self.title_rect.centerx+dx
        self.title_rect.centery = self.title_rect.centery+dy
        
    def reset(self):
        if self.val != self.val_orig:
            self.toggle()
            self.val = self.val_orig
        
    def toggle(self):
        if self.axis == 'y':
            self.image = pygame.transform.flip(self.image,0,1)
        else:
            self.image = pygame.transform.flip(self.image,1,0)
        self.val = not self.val
        
    def settitle(self,title=''):
        self.title = self.font.render(title,True,(0,0,0))
        tr_old = self.title_rect.copy()
        self.title_rect = self.title.get_rect()
        self.title = pygame.transform.smoothscale(self.title,(int(self.title_rect.width*tr_old.height/self.title_rect.height),tr_old.height))
        self.title_rect = self.title.get_rect(center=tr_old.center)
        
    def setcfg(self,port=0,pin=0):
        self.port = port
        self.pin = pin
        if self.title:
            self.settitle('P{}.{}'.format(self.port,self.pin))
    
    def draw(self,screen):
        screen.blit(self.image,self.rect)
        if self.labels:
            screen.blit(self.label0,self.label0_rect)
            screen.blit(self.label1,self.label1_rect)
        if self.title:
            screen.blit(self.title,self.title_rect)

class Pushbutton():
    def __init__(self,file0,file1,val,center=(0,0),scale=1,title='',axis='y',port=None,pin=None):
        self.val_orig = val
        self.val = val
        self.image0 = pygame.image.load(file0).convert_alpha()
        self.image1 = pygame.image.load(file1).convert_alpha()
        self.rect = self.image0.get_rect()
        self.image0 = pygame.transform.smoothscale(self.image0,(int(self.rect.width*scale),int(self.rect.height*scale)))
        self.image1 = pygame.transform.smoothscale(self.image1,(int(self.rect.width*scale),int(self.rect.height*scale)))
        self.rect = self.image0.get_rect()
        self.rect.center = center
        self.title = False
        self.font = pygame.font.SysFont('Serif', 18)
        self.port = port
        self.pin = pin
        
        self.image = self.image0
        
        if title or (self.port is not None and self.pin is not None):
            if not title:
                title = 'P{}.{}'.format(self.port,self.pin)
            self.title = self.font.render(title,True,(0,0,0))
            self.title_rect = self.title.get_rect()
            self.title = pygame.transform.smoothscale(self.title,(int(self.title_rect.width*scale),int(self.title_rect.height*scale)))
            self.title_rect = self.title.get_rect()
            if axis == 'y':
                self.title_rect.centerx = self.rect.centerx
                self.title_rect.bottom = self.rect.top - 5
            else:
                self.title_rect.right = self.rect.left-5
                self.title_rect.centery = self.rect.centery
                
    def adjustcenter(self,center=(0,0)):
        dx = center[0]-self.rect.centerx
        dy = center[1]-self.rect.centery
        
        self.rect.centerx = self.rect.centerx+dx
        self.rect.centery = self.rect.centery+dy
        self.title_rect.centerx = self.title_rect.centerx+dx
        self.title_rect.centery = self.title_rect.centery+dy
        
    def reset(self):
        self.val =self.val_orig
        self.image = self.image0
        
    def press(self):
        self.image = self.image1
        self.val = not self.val_orig
        
    def release(self):
        self.image = self.image0
        self.val = self.val_orig
        
    def settitle(self,title=''):
        self.title = self.font.render(title,True,(0,0,0))
        tr_old = self.title_rect.copy()
        self.title_rect = self.title.get_rect()
        self.title = pygame.transform.smoothscale(self.title,(int(self.title_rect.width*tr_old.height/self.title_rect.height),tr_old.height))
        self.title_rect = self.title.get_rect(center=tr_old.center)
    
    def setcfg(self,port=0,pin=0):
        self.port = port
        self.pin = pin
        if self.title:
            self.settitle('P{}.{}'.format(self.port,self.pin))
        
    def draw(self,screen):
        screen.blit(self.image,self.rect)
        if self.title:
            screen.blit(self.title,self.title_rect)

class Servo():
    def __init__(self,simstep=0.01):    # simstep is update interval in s
        self.desiredangle = 0   # degrees
        self.angle = 0      # degrees
        self.maxturn = 25   # degrees
        self.breakturn = 50
        self.maxchange = 200*simstep   # degrees/second
        
    def reset(self):
        self.angle = 0
        self.desiredangle = 0
    
    # Needs to be called every simulation step
    def update(self):
        offset = self.desiredangle-self.angle
        if offset:
            if abs(offset) > self.maxchange:
                offset = math.copysign(self.maxchange,offset)
            self.angle += offset
        if abs(self.angle) > self.maxturn:
            self.angle = math.copysign(self.maxturn,self.angle)
            
    def set(self,angle=0):
        if abs(angle) > self.maxturn:
            if abs(angle) > self.breakturn:
                self.desiredangle = 0
            else:
                self.desiredangle = -math.copysign(self.maxturn,angle)
        else:
            self.desiredangle = -angle
    
    def setdc(self,dc=0,per=0):   #pw in seconds
        # If outside of bounds, de-init the motor
        if per < 0.015 or per > 0.025:
            pass
        else:
            pw = dc*per
            self.set((pw-0.0015)/.0005*self.maxturn)

class Drive():
    def __init__(self,simstep=0.01,loaded=False):
        self.initd = False
        self.rel_pw = 0
        self.initd_count = 0
        self.initd_count_target = 0.9/simstep
        self.inittol = .25
        self.speed = 0
        self._speed_ = 0    # Speed calculation before offset applied
        self.speed_offset = 0   # Constant velocity offset (for PI labs)
        self.desiredspeed = 10 # cm/s?
        self.maxspeed = 50
        self.breakspeed = 100
        if loaded:
            self.maxchange = 50*simstep
        else:
            self.maxchange = 100*simstep
        
    def reset(self):
        self.initd = False
        self.initd_count = 0
        self._speed_ = 0
        self.speed = 0
        self.speed_offset = 0
        self.desiredspeed = 10
    
    # A constant perterbation offset specified by a ratio (perterbation/maxspeed)
    def setoffset(self,ratio):
        if ratio > 1:
            ratio = 1
        elif ratio < -1:
            ratio = -1
        self.speed_offset = ratio*self.maxspeed
        
    # Needs to be called every simulation step
    def update(self):
        if self.initd:
            offset = self.desiredspeed-self._speed_
#             if abs(offset) > self.maxchange:
#                 offset = math.copysign(self.maxchange,offset)
#                 self._speed_ += offset
#             else:  
#                 self._speed_ = self.desiredspeed
            if self._speed_ > 0 == offset < 0:   # If we are slowing down
                if abs(offset) > 2*self.maxchange:  # Check acceleration (can slow down faster)
                    offset = math.copysign(2*self.maxchange,offset)
                    self._speed_ += offset
                else:
                    self._speed_ = self.desiredspeed
            else: # We are speeding up
                if abs(offset) > self.maxchange:
                    offset = math.copysign(self.maxchange,offset)
                    self._speed_ += offset
                else:
                    self._speed_ = self.desiredspeed
                    
        elif abs(self.rel_pw) < 5e-6:
            self.initd_count += 1
            if self.initd_count >= self.initd_count_target:
                self.initd = True
        else:
            self.initd_count = 0
        self.speed = self._speed_ + self.speed_offset
                
    def set(self,speed=0):
        if abs(speed) > self.maxspeed:
            if abs(speed) > self.breakspeed:
                self.desiredspeed = 0
            else:
                self.desiredspeed = math.copysign(self.maxspeed,speed)
        else:
            self.desiredspeed = speed
            
    def setdc(self,dc=0,per=0):   #pw in seconds
        # If outside of bounds, de-init the motor
        if per < 0.015 or per > 0.025:
            self.initd = False 
            self.initd_count = 0
        else:
            self.rel_pw = dc*per-0.0015
            self.set((self.rel_pw)/.0004*self.maxspeed)
            
class LED():
    def __init__(self,simstep=0.01):
        self.state = 0      #0 off, 1 on, anything inbetween: brightness
        
    def reset(self):
        self.state = 0
            
    def setdc(self,dc=0,per=0):   #pw in seconds
        if per == 0:
            self.state = 1
        else:
            self.state = 1-dc
        
    def on(self):
        self.state = 1
    
    def off(self):
        self.state = 0
        
    def update(self):
        pass
            
class Obstacle():
    def __init__(self,radius=25,center=(0,0),amp=10,freq=0.5,simstep=0.01,rotate=True):
        self.run = False
        self.centered = True
        self.rotate = rotate
        #self.surf = pygame.Surface((size,size),pygame.SRCALPHA)
        self.rect = pygame.Rect(0,0,radius*2,radius*2)
        self.rect.center = center
        self.rot_rect = self.rect.copy()
        self.radius = radius
        self.amp = amp
        self.freq = 2*np.pi*freq
        self.step = simstep
        self.eyepos = self.rect.center
        
        self.t = 0
        self.direction = np.array([0,0])  # unit vector
        self.angle = 0
        
        self.reset()
        
    def reset(self):
        self.run = False
        self.centered = True
        self.speed = 0
        self.t = 0
        self.direction = 0
        self.rot_rect.center = self.rect.center
        self.eyepos = self.rect.center
        
    def update(self,looktowards=(0,0)):
        # move the obstacle
        if self.run or not self.centered:
            time_dep = np.sin(self.freq*self.t)
            self.rot_rect.center = tuple(self.amp*time_dep*self.direction+np.array(self.rect.center))
            self.t += self.step
            if not self.centered and not self.run:
                if (time_dep > 0) == (self.time_dep_last <= 0): 
                    self.rot_rect.center = self.rect.center
                    self.centered = True
            self.time_dep_last = time_dep
                
        v1 = np.array(looktowards) - np.array(self.rot_rect.center)
        #self.angle = 1.5*np.pi-np.arctan2(v1[1],v1[0])
        self.angle = np.arctan2(v1[1],v1[0])
        self.eyepos = tuple((np.array([self.radius*0.5*np.cos(self.angle),self.radius*0.5*np.sin(self.angle)])+np.array(self.rot_rect.center)).astype(int))
    
    def turnon(self,target=(0,0)):
        self.direction = np.array(target)-np.array(self.rect.center)
        self.direction = self.direction / np.linalg.norm(self.direction)
        self.run = True
        self.centered = False
        
    def turnoff(self):
        self.run = False
        
    def draw(self,surf):
        pygame.draw.circle(surf,(0,0,0),self.rot_rect.center,self.radius)
        pygame.draw.circle(surf,(150,90,255),self.rot_rect.center,int(self.radius*.8))
        pygame.draw.circle(surf,(0,0,0),self.eyepos,int(self.radius*.3))
        pygame.draw.circle(surf,(255,255,255),self.eyepos,int(self.radius*.15))
        
        
        
class Gondola():
    def __init__(self,asset_path,scale=1,center=(0,0),sym=True,simstep=0.01):
        # Initialize gondola 
        self.gond = pygame.image.load(asset_path+"Gondola/gondola.png").convert_alpha()
        (self.gond,self.rect_gond) = scaleImage(self.gond,scale)
        self.rect_gond.center = center
        
        
        
        
        # Initialize fans
        self.fans=[]
        self.fans.append(Fan((249,411),(19,94),port=0,pin=4,dir=1,sym=sym,simstep=simstep))
        self.fans.append(Fan((30,247),(94,19),port=0,pin=5,dir=1,sym=sym,simstep=simstep))
        self.fans.append(Fan((394,247),(94,19),port=0,pin=6,dir=-1,sym=sym,simstep=simstep))
        
        self.I = 1              # Moment of Inertia of gondola
        
        # These values are in TENTHS of DEGREES (original model did this)
        self.theta_orig = 0
        self.theta = 0
        self.theta_t = 0
        
        self.dt = simstep
        
        # Friction
        self.Mfs = 70
        self.Mfr = self.Mfs/2
        
        # Offset Torque
        #self.Mo = 100
        self.Mo = 0
        
        self.reset()
        
    def reset(self):
        self.theta = self.theta_orig
        self.theta_t = 0
        for fan in self.fans:
            fan.reset()
            
    def update(self):
        self.calcM()
        theta_tt = self.M/self.I
        theta_t_new = self.theta_t + theta_tt*self.dt
        if (theta_t_new > 0) == (self.theta_t < 0) and (self.theta_t != 0): # If velocity switches sign, set to 0 so static friction gets applied
            self.theta_t = 0
        else:
            self.theta_t = theta_t_new
        self.theta +=  self.theta_t*self.dt
        self.theta %= 3600
        for fan in self.fans:
            fan.update()
    
    def calcM(self):
        self.M = self.Mo    # Start with offset torque
        # Sum the moments from the fans
        for fan in self.fans:
            self.M += fan.getM()
        # Add friction
        if self.theta_t != 0: # Add rolling friction
            self.M -= np.copysign(self.Mfr,self.theta_t)
        else:
            if abs(self.M)>self.Mfs:
                self.M -= np.copysign(self.Mfs,self.M)
            else:
                self.M = 0
                
        # Calculate stopping moment, if necessary
        if (abs(self.theta_t) < 5)  and (abs(self.M) <= self.Mfr):
            self.M = -self.theta_t*self.I/self.dt
            
    def draw(self,screen):
        surf = self.gond.copy()
        for fan in self.fans:
            fan.draw(surf)
        surf.blit(self.gond,(0,0))
        surf = pygame.transform.rotozoom(surf,-self.theta/10, 1)
        rect = surf.get_rect(center=self.rect_gond.center)
        screen.blit(surf,rect)
        
        
class Fan():
    def __init__(self,corner=(0,0),size=(94,19),port=0,pin=0,dir=1,sym=True,simstep=0.01):
        self.initd = True 
        self.initd_count = 0
        self.initd_count_target = 0.9/simstep
        self.inittol = .25
        self.M = 0
        self.des_M = 0
        self.dir = dir
        self.port = port
        self.pin = pin
        self.ramp = 3000*simstep
        self.delay_active = True
        self.delay = 0
        self.simstep = simstep
        self.rect = pygame.Rect(corner,size)
        self.color = (255,255,255)
        self.sym = sym
        
    def reset(self):
        self.initd = True 
        self.delay_active = True
        self.delay = 0
        self.initd_count = 0
        self.M = 0
        self.des_M = 0
        self.color = [255,255,255]
    
    # Needs to be called every simulation step
    def update(self):
        if self.initd:
            if not self.delay_active:
                offset = self.des_M - self.M
                if abs(offset) > self.ramp:
                    offset = np.copysign(self.ramp,offset)
                newM = self.M + offset
                if ((newM > 0) == (self.M < 0)) and (self.M != 0):  # if sign switches (excluding case where we start form zero
                    newM = 0
                    self.delay_active = True
                    self.delay = 0
                self.M = newM
            else:
                self.delay += self.simstep
                # if self.delay > 0.75:
                if self.delay > 0.5:
                    self.delay_active = False
                    self.delay = 0
        #elif abs(self.des_M) < 0.1*self.max_M:
        #    self.initd_count += 1
        #    self.initd = True
        else:
            self.initd_count = 0
                
    def setdc(self,dc=0,per=0):   #pw in seconds
        Npw = (dc-0.075)*737/.02 #get pulsewidth counts relative to neutral
        self.setpw(Npw)
            

    def setpw(self,Npw=0,per=0.02):   #Npw in counts
        # Set pulsewidth limits
        if abs(Npw) > 1474:
            Npw = 0 
        elif abs(Npw) > 737:
            Npw = np.copysign(737,Npw)
        
        # apply moment equation
        if Npw < 0:
            if self.sym:
                M = Npw*(0.0011*abs(Npw)+0.7485)
            else:
                #M = Npw*(-4.6493e-4*Npw+0.1757)
                M = Npw*(0.0011*abs(Npw)+0.7485)/2
        else:
            M = Npw*(0.0011*Npw+0.7485)
        self.des_M = M
        self.setcolor()
    
    def getM(self):
        return self.M*self.dir
            
    def setcolor(self):
        if self.M < 0 and not self.sym:
            if self.M < -382:
                self.color = (0,0,255)
            else:
                c = 255-int(self.M*-0.668)
                self.color = (c,c,255)
        else:
            if abs(self.M) > 1149:
                c = 255
            else:
                c = 255-int(abs(self.M)*.222)
            if self.M < 0:
                self.color = (c,c,255)
            else:
                self.color = (255,c,c)
    
    def draw(self,surf):
        pygame.draw.rect(surf,self.color,self.rect)
        
        
class MovingBackground():
    def __init__(self,window_size,scale,linespacing=[50,50]):
        self.scale = scale;
        if type(linespacing) is int:
            linespacing = [linespacing]*2
        self.linespacingx = scaleCoord((linespacing[0],0),self.scale)
        self.linespacingy = scaleCoord((0,linespacing[1]),self.scale)
        self.offsets = np.array([self.linespacingx[0],self.linespacingy[1]])
        self.background = pygame.Surface(window_size+4*self.linespacingx+2*self.linespacingy).convert()
        self.background.fill((225,225,225))
        self.background_rect = self.background.get_rect(left=-self.offsets[0],top=-self.offsets[1])
        _locx = 0
        _locy = 0
        while _locx <= self.background_rect.width:
            pygame.draw.line(self.background,(255,255,255),(_locx,0),(_locx,self.background_rect.height),2)
            _locx += self.offsets[0]
        while _locy <= self.background_rect.height:
            pygame.draw.line(self.background,(255,255,255),(0,_locy),(self.background_rect.width,_locy),2)
            _locy += self.offsets[1]
        self.tracking = np.array([0.,0.])        # Track background location in order to not lose info
        self.background_rect_moved = self.background_rect.copy()
        self.background_rect_moved.topleft = -self.offsets
        
    def reset(self):
        self.background_rect_moved.topleft = -self.offsets
        self.tracking *= 0
        
    def update(self,loc_diff):
        self.tracking -= loc_diff
        if abs(self.tracking[0]) > self.offsets[0]:
            self.tracking[0] -= math.copysign(self.offsets[0], self.tracking[0])
        if abs(self.tracking[1]) > self.offsets[1]:
            self.tracking[1] -= math.copysign(self.offsets[1], self.tracking[1])
        self.background_rect_moved.topleft = (self.tracking - self.offsets).astype(int)
        
    def blit(self,surf):
        surf.blit(self.background,self.background_rect_moved)
        
if __name__ == "__main__":
    import code
    pygame.init()
    screen = pygame.display.set_mode((800,800))
    asset_path = "../assets/"
    car = DrivingCar(asset_path,scale=0.1)
    code.interact(local=dict(globals(), **locals()))
        
        
        
        
        
        
