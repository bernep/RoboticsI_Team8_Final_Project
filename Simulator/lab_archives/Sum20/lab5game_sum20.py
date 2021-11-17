import pygame,math
import numpy as np
import sys,os
from labcommon import * # @UnresolvedImport
from version import SIMULATOR_VERSION
import random

INFOA = "LITEC Lab 5 Simulator"
INFOB = INFOA+" Version "+SIMULATOR_VERSION

SIMSTEP = 0.01 # seconds between updates

class Simulation():
    def __init__(self,controlmodel,runctl,asset_path=None):
        self.ctlmod = controlmodel
        self.runctl = runctl
        self.cfgdone = False
        # Initialize screen
        pygame.init()
        pygame.font.init()
        self.clock = pygame.time.Clock()
        
        self.size = np.array((1200,400))
        
        # Ensure that display is large enough to show game window, if not, shrink
        dispsize = pygame.display.Info()
        self.scale = min(dispsize.current_w*0.95/self.size[0],dispsize.current_h*0.9/self.size[1])
        if self.scale >= 1:
            self.scale = 1
        else:
            self.size = (np.array(self.size)*self.scale).astype(int)
            
        self.screen = pygame.display.set_mode(self.size)
        pygame.display.set_caption(INFOA)
        pygame.display.set_icon(pygame.image.load(asset_path+"icon.png"))
        
        # Set background
        #self.background = pygame.Surface(self.screen.get_size()).convert()
        #self.background.fill((225,225,225))
        
        # Make moving background
        linespacing = scaleCoord((50,0),self.scale)
        self.background_offset = linespacing[0]
        self.background = pygame.Surface(self.size+2*linespacing).convert()
        self.background.fill((225,225,225))
        self.background_rect = self.background.get_rect(left=-self.background_offset)
        _loc = 0
        while _loc <= self.background_rect.width:
            pygame.draw.line(self.background,(255,255,255),(_loc,0),(_loc,self.size[0]),2)
            _loc += self.background_offset
        self.background_track = 0        # Track background location in order to not lose info
        self.background_rect_moved = self.background_rect.copy()
        self.background_rect_moved.left = -self.background_offset
        
        
        self.car = DrivingCar(asset_path,
                              scale=0.08*self.scale,
                              center=scaleCoord((self.size[0]/2,self.size[1]/2),self.scale),
                              angle=270,
                              simstep=SIMSTEP)
        
        # Set scaling of speed
        self.car.Drive.maxspeed *=self.scale*2
        self.car.Drive.breakspeed *=self.scale*2
        self.car.start_speed *= self.scale*2
        self.car.dead_speed *= self.scale*2
        self.car.Drive.maxchange *= self.scale*2
        
        self.velocity = 20                      # pixels per second
        self.velocity_limits = 50*self.scale   # pixels per second
        self.v_time_to_change = 2   # Seconds
        self.velocity_div = 0
        
        self.force = 0          # Pixels per second
        self.force_delay = 2    # Pixels per second
        self.force = 0 #random.randint(25,50)/100*random.randrange(-1,3,2)
        
        #self.target = Obstacle(radius=15,center=scaleCoord((1100,400),self.scale),freq=0.1,amp=int(350*self.scale))
        
        self.font = pygame.font.SysFont('Serif', 14)
        self.info = self.font.render(INFOB,True,(0,0,0))
        self.info_rect = self.info.get_rect()
        self.info_rect.bottomleft = (5,self.size[1])
        
        self.end = 0
        
        self.cfgdone = True
        
#         self.startup()
        
        
    def reset(self):
        self.car.reset()
        print(self.car.pos_x)
        self.velocity = 2
        self.v_time_to_change = 2
        self.force = 50/100*random.randrange(-1,3,2)
        self.end = 0
        
    def update(self):
        
        # Wait delay and then apply offset force.  Only do this once
        if self.force_delay > 0:
            self.force_delay -= SIMSTEP
            if self.force_delay <= 0:
                self.car.Drive.setoffset(self.force)
                
        # Wait delay for velocity change
        self.v_time_to_change -= SIMSTEP
        if self.v_time_to_change <= 0:
            #self.velocity = random.uniform(-self.velocity_limits,self.velocity_limits)
            velocity_div = random.randint(-4,4)
            #velocity_div = random.choice([-1,1])
            while velocity_div == self.velocity_div:
                velocity_div = random.randint(-4,4)
                #velocity_div = random.choice([-1,1])
            self.velocity_div = velocity_div
                
            if velocity_div == 0:
                self.velocity = 0
            else:
                self.velocity = self.velocity_limits/velocity_div

            self.v_time_to_change = 10
        
        # Update mechanical components
        #self.car.Servo.setdc(self.ctlmod.xbr.getpin(0,4,'CCM'),self.ctlmod.pca0.Tperiod)
        self.car.Drive.setdc(self.ctlmod.xbr.getpin(0,5,'CCM'),self.ctlmod.pca0.Tperiod)
        
        # Move the car
        self.car.update()
        # Ensure that the car doesn't move vertically.
        self.car.angle = np.radians(270)
        self.car.pos_y = self.car.pos_y_orig
       
        # Setpoint stored in "actuator" speed
        #self.ctlmod.actuator.setspeed(abs(self.velocity/self.velocity_limits)*255)
        #if self.velocity < 0:
        #    self.ctlmod.actuator.setdirectionraw(0)
        #lse:
        #    self.ctlmod.actuator.setdirectionraw(1)
        self.ctlmod.actuator.setspeed(abs(self.car.pos_x - self.size[0]/2)/(self.size[0]/2)*256)
        if self.car.pos_x < self.size[0]/2:
            self.ctlmod.actuator.setdirectionraw(0)
        else:
            self.ctlmod.actuator.setdirectionraw(1)
            
        # Export the speed to the ADC
        #print(((self.car.Drive.speed+self.velocity)/self.car.Drive.breakspeed+1)*1.2)
        self.ctlmod.xbr.setpin(1,7,((self.car.Drive.speed+self.velocity)/self.car.Drive.breakspeed+1)*1.2)
            
        # Move the background and car
        pxmove = self.velocity*SIMSTEP
        self.background_track += pxmove
        if abs(self.background_track) > self.background_offset:
            if self.background_track < 0:
                self.background_track += self.background_offset
            else:
                self.background_track -= self.background_offset
        self.background_rect_moved.left = int(self.background_track) -self.background_offset
        self.car.pos_x = self.car.pos_x + pxmove
        #print('{} {} {} {}'.format(self.velocity, self.background_offset,self.background_track,self.background_rect_moved.left))
        
        # Update peripheral timing
        self.ctlmod.timestep(SIMSTEP)
        
    def checkdone(self):
        if not self.car.rect.colliderect(self.background.get_rect()):
            self.end = -1
        return bool(self.end)
            
    def setconfig(self,cfg):
        # Not config for this one
        self.cfgdone = True
        
    def blit(self):
        self.screen.blit(self.background,self.background_rect_moved)
        
        pygame.draw.circle(self.screen,(0,0,0),(self.size/2).astype(int),int(100*self.scale),width=2)
        pygame.draw.circle(self.screen,(0,0,0),(self.size/2).astype(int),int(75*self.scale),width=2)
        pygame.draw.circle(self.screen,(0,0,0),(self.size/2).astype(int),int(50*self.scale),width=2)
        
        self.car.draw(self.screen)
        
        #if self.cfgdone:
            #pygame.draw.rect(self.screen,(255,255,255),self.startrect,width=3)
            #pygame.draw.rect(self.screen,(255,255,255),self.endrect,width=3)
            #self.screen.blit(self.endtext,self.rect_endtext)
        
        self.screen.blit(self.info,self.info_rect)
        
        
        
        font = pygame.font.SysFont('Serif', 30,bold=True)
        if not self.cfgdone:
            endrect = pygame.Rect((0,0),(400,100))
            endrect.center = (400,600)
            endtext1 = font.render('RIN NOT PROVIDED',True,(0,0,0))
            endtext1_rect = endtext1.get_rect(center=endrect.center)
            endtext1_rect.bottom = endrect.centery-3
            endtext2 = font.render('#define RIN xxxxxxxxx',True,(255,0,0))
            endtext2_rect = endtext2.get_rect(center=endrect.center)
            endtext2_rect.top = endrect.centery+3
            pygame.draw.rect(self.screen,(0,0,0),endrect,width=5)
            pygame.draw.rect(self.screen,(255,255,255),endrect)
            self.screen.blit(endtext1,endtext1_rect)
            self.screen.blit(endtext2,endtext2_rect)
        
        
        
            
    def run(self):
        while self.runctl > 0:
            if self.runctl == 2:
                self.runctl.run = 1
                self.reset()
            if self.runctl > 2:
                self.setconfig(self.runctl.run)
                self.runctl.run = 1
                self.reset()
            
            if not self.checkdone():
                self.update()
                    
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit()
                        return
                self.blit()
                
            else:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit()
                        return
                    
                font = pygame.font.SysFont('Serif', 30,bold=True)
                if self.end == -2:
                    endrect = pygame.Rect((0,0),(400,100))
                    endrect.center = scaleCoord(self.size/2,self.scale)
                    endtext = font.render('COURSE COMPLETE',True,(0,200,0))
                    endrect.center = (400,200)
                    endtext = font.render('OUT OF BOUNDS',True,(255,0,0))
                    pygame.draw.rect(self.screen,(0,0,0),endrect,width=5)
                    pygame.draw.rect(self.screen,(255,255,255),endrect)
                    self.screen.blit(endtext,endtext.get_rect(center=endrect.center))

            pygame.display.flip()

            self.clock.tick(1/SIMSTEP)
                
            
        
if __name__ == "__main__":
    sim = Simulation(0,1,'../assets/')
    sim.run()
        
        
        
