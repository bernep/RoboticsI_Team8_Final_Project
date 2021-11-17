import pygame,math
import numpy as np
import sys,os
from labcommon import * # @UnresolvedImport
from version import SIMULATOR_VERSION

INFOA = "LITEC Lab 4 Simulator"
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
        
        self.size = np.array((1200,800))
        
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
                              scale=0.08*self.scale,
                              center=scaleCoord((100,100),self.scale),
                              angle=180,
                              simstep=SIMSTEP)
        
        # Set scaling of speed
        self.car.Drive.maxspeed *=self.scale
        self.car.start_speed *= self.scale
        self.car.dead_speed *= self.scale
        self.car.Drive.maxchange *= self.scale
        
        
        self.target = Obstacle(radius=15,center=scaleCoord((1100,400),self.scale),freq=0.1,amp=int(350*self.scale))
        
        self.font = pygame.font.SysFont('Serif', 14)
        self.info = self.font.render(INFOB,True,(0,0,0))
        self.info_rect = self.info.get_rect()
        self.info_rect.bottomleft = (5,self.size[1])
        
        ss_path = asset_path + '/switch.png'
        self.SS = []
        self.SS.append(SlideSwitch(ss_path,
                                   val=0,
                                   center=scaleCoord((100,750),self.scale),
                                   scale=self.scale,
                                   labels=True,
                                   axis='x',
                                   port=3,
                                   pin=6))
        self.SS.append(SlideSwitch(ss_path,
                                   val=0,
                                   center=scaleCoord((100,700),self.scale),
                                   scale=self.scale,
                                   labels=True,
                                   axis='x',
                                   port=3,
                                   pin=7))
        
        
        self.PB = Pushbutton(asset_path+'/pb-unpressed.png',
                             asset_path+'/pb-pressed.png',
                             val=1,
                             center=scaleCoord((100,650),self.scale),
                             scale=self.scale,
                             axis='x',
                             port=3,
                             pin=0)
    
        self.end = 0
        
        
        self.wall = pygame.Surface(scaleCoord((15,800),self.scale)).convert()
        self.wall.fill((127,0,0))
        pygame.draw.rect(self.wall,(0,0,0),self.wall.get_rect(),width=5)
        self.wall1 = self.wall.get_rect(topleft=(int(400*self.scale),0))
        self.wall2 = self.wall.get_rect(topleft=(int(800*self.scale),0))
        self.wall1_active = True
        self.wall2_active = True
        
        self.cfgdone = True
        
        self.startup()
        
        
    def startup(self):
        self.car.Servo.angle = 10
        self.car.Servo.desiredangle = 10
        self.car.Drive.speed = 0
        self.car.Drive.desiredspeed = 100
        self.car.Drive.initd = True
        
    def reset(self):
        self.car.reset()
        self.target.reset()
        self.target.turnon(self.target.rect.midtop)
        self.wall1_active = True
        self.wall2_active = True
        self.end = 0
        
        
        ## Comment to not reset SlideSwitches, let state propogate
        #for SS in self.SS:
        #    SS.reset()  
    
    def detectwall(self,xloc):
        # Get location of ranger
        #transformation matrix
        
        # Check angle of wall, wall is directly right, so to get perpendicular, 
        # ranger needs to have been with 90 in it
        cara = np.unwrap([-self.car.angle])
        cara %= np.pi*2
        ang1 = np.unwrap((cara+self.car.r_beam))
        ang1 %= np.pi*2
        ang2 = np.unwrap((cara-self.car.r_beam))
        ang2 %= np.pi*2
        
        anglesin = np.sin(-self.car.angle)
        anglecos = np.cos(-self.car.angle)
        txmatrix = np.array([[anglecos,-anglesin],[anglesin,anglecos]])
        r_rel = txmatrix.dot(self.car.r_vec)+self.car.center()
        x_dist = xloc-r_rel[0]
        #print(' ')
        #print(x_dist)
        #print(np.degrees(cara))
        #print(np.degrees(ang1))
        #print(np.degrees(ang2))
        if x_dist < 0:
            return 500
        if (np.degrees(ang1) > 90) and (np.degrees(ang2) < 90):
            return min(int(x_dist/self.scale),500)
        if (np.degrees(ang1) < 90) and (np.degrees(ang1) > 0):
            ang1 = np.pi/2 - ang1
            return min(int((x_dist/np.cos(ang1))/self.scale),500)
        if (np.degrees(ang2) > 90) and (np.degrees(ang2) <180):
            ang2 -= np.pi/2
            return min(int((x_dist/np.cos(ang2))/self.scale),500)
        return 500
                
                
            
        
        

        
    def update(self):
        # Update peripheral timing
        self.ctlmod.timestep(SIMSTEP)
        
        # Update mechanical components
        self.car.Servo.setdc(self.ctlmod.xbr.getpin(0,4,'CCM'),self.ctlmod.pca0.Tperiod)
        self.car.Drive.setdc(self.ctlmod.xbr.getpin(0,5,'CCM'),self.ctlmod.pca0.Tperiod)
        
        # Move the car
        self.car.update()
        
        self.target.update(looktowards=self.car.center())
        if self.wall1_active:
            dist = self.detectwall(self.wall1[0])
            self.ctlmod.ranger.setecho(dist)
            if self.ctlmod.actuator.status and dist < 100 and self.car.Drive.speed < 0.1*self.car.Drive.maxspeed:
                self.wall1_active = False
        elif self.wall2_active:
            dist = self.detectwall(self.wall2[0])
            self.ctlmod.ranger.setecho(dist)
            if self.ctlmod.actuator.status and dist < 100 and self.car.Drive.speed < 0.1*self.car.Drive.maxspeed:
                self.wall2_active = False
        else:
            self.car.collidecirc(self.target.rot_rect.center,self.target.radius)
            self.ctlmod.ranger.setecho(self.car.detectobstacle())
        
        # Emit the switch values
        for SS in self.SS:
            self.ctlmod.xbr.setpin(SS.port,SS.pin,SS.val)
        # Emit the PB value
        self.ctlmod.xbr.setpin(self.PB.port,self.PB.pin,self.PB.val)
            
        # report sensor values
            
        self.ctlmod.compass.setdirection(-self.car.t_angle)
        self.ctlmod.actuator.setspeed(0) # I'm not implementing this now
        self.ctlmod.actuator.setdirection(self.target.angle)
        
    def checkdone(self):
        if self.car.collidecirc(self.target.rot_rect.center,self.target.radius):
            self.end = 1
        elif (self.car.rect.colliderect(self.wall1) and self.wall1_active) or (self.car.rect.colliderect(self.wall2) and self.wall2_active):
            self.end = -1
        elif not self.car.rect.colliderect(self.background.get_rect()):
            self.end = -1
        return bool(self.end)
            
    def setconfig(self,cfg):
        # Not config for this one
        self.cfgdone = True
        
        
    
    def blit(self):
        self.screen.blit(self.background,(0,0))
        
        self.car.draw(self.screen)
        
        #if self.cfgdone:
            #pygame.draw.rect(self.screen,(255,255,255),self.startrect,width=3)
            #pygame.draw.rect(self.screen,(255,255,255),self.endrect,width=3)
            #self.screen.blit(self.endtext,self.rect_endtext)
        
        self.target.draw(self.screen)
        
        for SS in self.SS:
            SS.draw(self.screen)
        self.PB.draw(self.screen)
            
        self.screen.blit(self.info,self.info_rect)
        
        if self.wall1_active:
            self.screen.blit(self.wall,self.wall1)
        if self.wall2_active:
            self.screen.blit(self.wall,self.wall2)
        
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
                    elif event.type == pygame.MOUSEBUTTONDOWN:
                        pos = pygame.mouse.get_pos()
                        for SS in self.SS:
                            if SS.rect.collidepoint(pos):
                                SS.toggle()
                        if self.PB.rect.collidepoint(pos):
                            self.PB.press()
                    elif event.type == pygame.MOUSEBUTTONUP:
                        self.PB.release()
                        self.compassnorth_hit = False
                        
                self.blit()
                
            else:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit()
                        return
                    
                font = pygame.font.SysFont('Serif', 30,bold=True)
                if self.end == 1:
                    endrect = pygame.Rect((0,0),(400,100))
                    endrect.center = scaleCoord(self.size/2,self.scale)
                    endtext = font.render('COURSE COMPLETE',True,(0,200,0))
                    pygame.draw.rect(self.screen,(0,0,0),endrect,width=5)
                    pygame.draw.rect(self.screen,(255,255,255),endrect)
                    self.screen.blit(endtext,endtext.get_rect(center=endrect.center))
                elif self.end == -1:
                    endrect = pygame.Rect((0,0),(300,100))
                    endrect.center = scaleCoord(self.size/2,self.scale)
                    endtext = font.render('COURSE COMPLETE',True,(0,200,0))
                    endtext = font.render('CRASH!',True,(255,0,0))
                    pygame.draw.rect(self.screen,(0,0,0),endrect,width=5)
                    pygame.draw.rect(self.screen,(255,255,255),endrect)
                    self.screen.blit(endtext,endtext.get_rect(center=endrect.center))
                elif self.end == -2:
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
        
        
        
