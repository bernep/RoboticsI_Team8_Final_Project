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
        self.background = MovingBackground(self.size,self.scale,linespacing=50)
        
        
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
                                   title='Disable Compass Noise'))
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
        
        self.pw_offset_sign = 1;
        
        self.des_heading = 90
        self.compassnorth = pygame.image.load(asset_path+"compassarrow.png").convert_alpha()
        self.compassnorth_rect = self.compassnorth.get_rect()
        self.compassnorth_rect.center = (550,50)
        self.compassnorth_rot = self.compassnorth.copy()
        
        self.noise_stddev = 0
        self.steer_offset = 0
        
        self.align_time = 0
        self.aligned = 0
        self.align_tol = np.radians(2) # pm 2 Degree tolerance
        self.align_duration = 5 # 5 Seconds
        self.align_error = 180
        
        # Print out location and sizing:
        self.heading_print = (np.array([5,5])*self.scale).astype(int)
        self.error_print = (np.array([5,5+25])*self.scale).astype(int)
        self.time_print = (np.array([5,5+2*25])*self.scale).astype(int)
        self.font = pygame.font.SysFont('Serif',int(20*self.scale))
        
        self.startup()
        
        
    def startup(self):
        self.car.Servo.angle = 10
        self.car.Servo.desiredangle = 10
        self.car.Drive.speed = 0
        self.car.Drive.desiredspeed = 100
        self.car.Drive.initd = True
        
    def reset(self):
        self.end = 0;
        self.background.reset()
        self.car.reset()
        self.des_heading = 0;
        self.compassnorth_rot = self.compassnorth.copy()
        self.align_time = 0
        self.aligned = 0
        
        
        ## Comment to not reset SlideSwitches, let state propogate
        #for SS in self.SS:
        #    SS.reset()  
    
    def update(self):
        # Update peripheral timing
        self.ctlmod.timestep(SIMSTEP)
        
        # Update mechanical components
        #self.car.Servo.setdc(self.ctlmod.xbr.getpin(0,4,'CCM')+self.pw_offset_sign*0.005,self.ctlmod.pca0.Tperiod)
        self.car.Servo.setdc(self.ctlmod.xbr.getpin(0,4,'CCM')+self.steer_offset/200*0.005,self.ctlmod.pca0.Tperiod)
        self.car.Drive.setdc(self.ctlmod.xbr.getpin(0,5,'CCM'),self.ctlmod.pca0.Tperiod)
        
            
        # Move the car
        self.car.update()
        
        # Move the background and recenter car
        self.background.update(self.car.center()-self.car.centerorig())
        
        self.car.setcenter(self.car.centerorig())
                
        # report sensor values
        if self.SS[0].val:
            angle_val = -self.car.angle
        else:
            angle_val = -self.car.angle+np.random.normal(0,self.noise_stddev)
        self.ctlmod.compass.setdirection(angle_val)
        
        self.align_error = (np.radians(self.des_heading) + self.car.angle) % (2*np.pi)
        if self.align_error > np.pi:
            self.align_error -= 2*np.pi
        
        if abs(self.align_error) < self.align_tol:
            self.align_time += SIMSTEP
            if self.align_time >= self.align_duration:
                if not self.aligned:
                    self.ctlmod.aux.data_out[0] += 1
                    self.aligned = True
        else:
            self.align_time = 0
            
        
        while self.ctlmod.aux.in_buffer:
            cmd = self.ctlmod.aux.get_next()
            if cmd:
                new_angle = (cmd[1]*256+cmd[2])/10
                if self.des_heading != new_angle:
                    self.des_heading = new_angle
                    self.compassnorth_rot = pygame.transform.rotozoom(self.compassnorth,-self.des_heading,1)
                    self.noise_stddev = np.radians(random.randrange(1,10))
                    if not self.SS[1].val:
                        self.steer_offset = random.randrange(-200,200)
                    self.aligned = False
                    self.align_time = 0
                #if not cmd[3]:
                #    self.noise_stddev = 0
                #if not cmd[4]:
                #    self.steer_offset = 0
                    
        
    def checkdone(self):
        return 0
            
    def setconfig(self,cfg):
        # Not config for this one
        self.cfgdone = True
        
        
    
    def blit(self):
        self.background.blit(self.screen)
        
        self.car.draw(self.screen)
        
        for SS in self.SS:
            SS.draw(self.screen)
        
        #if self.cfgdone:
            #pygame.draw.rect(self.screen,(255,255,255),self.startrect,width=3)
            #pygame.draw.rect(self.screen,(255,255,255),self.endrect,width=3)
            #self.screen.blit(self.endtext,self.rect_endtext)
        
        self.screen.blit(self.info,self.info_rect)
        
        self.screen.blit(self.compassnorth_rot,self.compassnorth_rect)
        
        
        if abs(self.align_error) <= self.align_tol:
            err_color = (0,150,0)
        else:
            err_color = (200,0,0)
        self.screen.blit(self.font.render("Error:",True,err_color),self.error_print)
        txt = self.font.render("{:5.1f}\u00b0".format(np.degrees(self.align_error)),True,err_color)
        self.screen.blit(txt,(175-txt.get_width(),self.error_print[1]))
        self.screen.blit(self.font.render("Heading:",True,(0,0,0)),self.heading_print)
        txt = self.font.render("{:5.1f}\u00b0".format(np.degrees(-self.car.angle)%360),True,(0,0,0))
        self.screen.blit(txt,(175-txt.get_width(),self.heading_print[1]))
        self.screen.blit(self.font.render("Aligned Time:",True,(0,0,0)),self.time_print)
        txt = self.font.render("{:5.1f} s".format(self.align_time),True,(0,0,0))
        self.screen.blit(txt,(175-txt.get_width(),self.time_print[1]))
        
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
                elif event.type == pygame.KEYDOWN:
                    delta = 20
                    if event.key == pygame.K_a:
                        self.car.pos_x -= delta
                    elif event.key == pygame.K_s:
                        self.car.pos_y += delta
                    elif event.key == pygame.K_d:
                        self.car.pos_x += delta
                    elif event.key == pygame.K_w:
                        self.car.pos_y -= delta
                    elif event.key == pygame.K_q:
                        self.car.angle += np.pi/20
                    elif event.key == pygame.K_e:
                        self.car.angle -= np.pi/20
                    elif event.key == pygame.K_PERIOD:
                        self.speed_change(1)
                    elif event.key == pygame.K_COMMA:
                        self.speed_change(-1)
                    elif event.key == pygame.K_0:
                        self.speed_change(0)
                    else:
                        print(event.key)
                    
            self.blit()
                
            pygame.display.flip()

            self.clock.tick(1/SIMSTEP)
                
            
        
if __name__ == "__main__":
    sim = Simulation(0,1,'../assets/')
    sim.run()
        
        
        
