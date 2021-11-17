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
        
        self.size = np.array((600,600))
        
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
        self.background = pygame.Surface(self.screen.get_size()).convert()
        self.background.fill((225,225,225))
        
        
        self.car = DrivingCar(asset_path,
                              scale=0.12*self.scale,
                              center=scaleCoord((self.size[0]/2,self.size[1]/2),self.scale),
                              angle=180,
                              simstep=SIMSTEP)
        
        # Set scaling of speed
        self.car.Drive.maxspeed *=self.scale*2
        self.car.Drive.breakspeed *=self.scale*2
        self.car.start_speed *= self.scale*2
        self.car.dead_speed *= self.scale
        self.car.Drive.maxchange *= self.scale*2
        self.car.Servo.breakturn = 10000
        
        # Make moving background
        linespacingx = scaleCoord((50,0),self.scale)
        linespacingy = scaleCoord((0,50),self.scale)
        self.backgroundx_offset = linespacingx[0]
        self.backgroundy_offset = linespacingy[1]
        self.background = pygame.Surface(self.size+4*linespacingx+2*linespacingy).convert()
        self.background.fill((225,225,225))
        self.background_rect = self.background.get_rect(left=-self.backgroundx_offset,top=-self.backgroundy_offset)
        _locx = 0
        _locy = 0
        while _locx <= self.background_rect.width:
            pygame.draw.line(self.background,(255,255,255),(_locx,0),(_locx,self.background_rect.height),2)
            _locx += self.backgroundx_offset
        while _locy <= self.background_rect.height:
            pygame.draw.line(self.background,(255,255,255),(0,_locy),(self.background_rect.width,_locy),2)
            _locy += self.backgroundy_offset
        self.backgroundx_track = 0        # Track background location in order to not lose info
        self.backgroundy_track = 0        # Track background location in order to not lose info
        self.background_rect_moved = self.background_rect.copy()
        self.background_rect_moved.topleft = (-self.backgroundx_offset,-self.backgroundy_offset)
        
        
        self.SS = []
        ss_path = asset_path + '/switch.png'
        self.SS.append(SlideSwitch(ss_path,
                                   val=0,
                                   center=scaleCoord((540,575),self.scale),
                                   scale=self.scale,
                                   labels=True,
                                   axis='x',
                                   port=3,
                                   pin=6,
                                   title='Disable \'North\' Randomizing'))
        self.SS.append(SlideSwitch(ss_path,
                                   val=0,
                                   center=scaleCoord((540,525),self.scale),
                                   scale=self.scale,
                                   labels=True,
                                   axis='x',
                                   port=3,
                                   pin=5,
                                   title='Disable Error Randomizing'))
        
        self.font = pygame.font.SysFont('Serif', 14)
        self.info = self.font.render(INFOB,True,(0,0,0))
        self.info_rect = self.info.get_rect()
        self.info_rect.bottomleft = (5,self.size[1])
        
        self.cfgdone = True
        
        self.north = 0
        self.north_count = 0;
        self.north_count_change = 10
        
        self.pw_offset_sign = 1;
        
        self.compassnorth = pygame.image.load(asset_path+"compassnorth.png").convert_alpha()
        self.compassnorth_rect = self.compassnorth.get_rect()
        self.compassnorth_rect.center = (550,50)
        self.compassnorth_rot = self.compassnorth.copy()
        
        self.startup()
        
        
    def startup(self):
        self.car.Servo.angle = 10
        self.car.Servo.desiredangle = 10
        self.car.Drive.speed = 0
        self.car.Drive.desiredspeed = 100
        self.car.Drive.initd = True
        
    def reset(self):
        self.end = 0;
        self.car.reset()
        self.north_count = 0;
        self.north = 0;
        self.compassnorth_rot = self.compassnorth.copy()
        
        
        ## Comment to not reset SlideSwitches, let state propogate
        #for SS in self.SS:
        #    SS.reset()  
    
    def update(self):
        # Update peripheral timing
        self.ctlmod.timestep(SIMSTEP)
        
        # Update mechanical components
        self.car.Servo.setdc(self.ctlmod.xbr.getpin(0,4,'CCM')+self.pw_offset_sign*0.005,self.ctlmod.pca0.Tperiod)
        self.car.Drive.setdc(self.ctlmod.xbr.getpin(0,5,'CCM'),self.ctlmod.pca0.Tperiod)
        
            
        # Move the car
        self.car.update()
        
        # Move the background and recenter car
        self.backgroundx_track -= self.car.pos_x - self.car.pos_x_orig
        self.backgroundy_track -= self.car.pos_y - self.car.pos_y_orig
        self.car.pos_x = self.car.pos_x_orig
        self.car.pos_y = self.car.pos_y_orig
        if abs(self.backgroundx_track) > self.backgroundx_offset:
            if self.backgroundx_track < 0:
                self.backgroundx_track += self.backgroundx_offset
            else:
                self.backgroundx_track -= self.backgroundx_offset
        if abs(self.backgroundy_track) > self.backgroundy_offset:
            if self.backgroundy_track < 0:
                self.backgroundy_track += self.backgroundy_offset
            else:
                self.backgroundy_track -= self.backgroundy_offset
                
        self.background_rect_moved.left = int(self.backgroundx_track) -self.backgroundx_offset
        self.background_rect_moved.top = int(self.backgroundy_track) -self.backgroundy_offset

        #self.ctlmod.ranger.setecho(self.car.detectobstacle())
        
        # report sensor values
        self.ctlmod.compass.setdirection(-(np.radians(self.north)-(self.car.angle)))
        self.north_count += SIMSTEP
        if self.north_count >= self.north_count_change:
            if not self.SS[1].val:
                self.pw_offset_sign = random.randint(0,1)*2-1
            else:
                print("not updating")
            north_new = self.north
            self.north_count = 0
            while self.north == north_new:
                north_new = random.randint(0,3)*90
            if not self.SS[0].val:
                self.north = north_new
                self.compassnorth_rot = pygame.transform.rotozoom(self.compassnorth,self.north,1)
            
            
        
        
    def checkdone(self):
        return 0
            
    def setconfig(self,cfg):
        # Not config for this one
        self.cfgdone = True
        
        
    
    def blit(self):
        self.screen.blit(self.background,self.background_rect_moved)
        
        self.car.draw(self.screen)
        
        for SS in self.SS:
            SS.draw(self.screen)
        
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
        
        
            
        self.screen.blit(self.compassnorth_rot,self.compassnorth_rect)
        
        
        
            
    def run(self):
        while self.runctl > 0:
            if self.runctl == 2:
                self.runctl.run = 1
                self.reset()
            if self.runctl > 2:
                self.setconfig(self.runctl.run)
                self.runctl.run = 1
                self.reset()
            
            self.update()
                    
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    return
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    pos = pygame.mouse.get_pos()
                    for SS in self.SS:
                        if SS.rect.collidepoint(pos):
                            SS.toggle()
                    
            self.blit()
                
            pygame.display.flip()

            self.clock.tick(1/SIMSTEP)
                
            
        
if __name__ == "__main__":
    sim = Simulation(0,1,'../assets/')
    sim.run()
        
        
        
