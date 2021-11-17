# Template: https://www.pygame.org/docs/tut/tom_games2.html
import pygame,math
import numpy as np
import sys,os
from labcommon import * # @UnresolvedImport
from version import SIMULATOR_VERSION

INFOA = "LITEC Lab 3 Simulator"
INFOB = INFOA+" Version "+SIMULATOR_VERSION

SIMSTEP = 0.01 # seconds between updates

class Simulation():
    def __init__(self,controlmodel,runctl,asset_path=None):
        self.ctlmod = controlmodel
        self.runctl = runctl
        # Initialize screen
        pygame.init()
        pygame.font.init()
        self.clock = pygame.time.Clock()
        
        self.size = (1200,800)
        
        # Ensure that display is large enough to show game window, if not, shrink
        dispsize = pygame.display.Info()
        self.scale = min(dispsize.current_w*0.95/self.size[0],dispsize.current_h*0.9/self.size[1])
        if self.scale >= 1:
            self.scale = 1
        else:
            self.size = tuple((np.array(self.size)*self.scale).astype(int))
        
        self.screen = pygame.display.set_mode(self.size)
        pygame.display.set_caption(INFOA)
        pygame.display.set_icon(pygame.image.load(asset_path+"icon.png"))
        
        # Set background
        self.background = pygame.Surface(self.screen.get_size()).convert()
        self.background.fill((225,225,225))
        
        # Get file locations
        if asset_path is None:
            try:
                base_path = sys._MEIPASS #@UndefinedVariable
            except Exception:
                base_path = os.path.abspath(".")
            asset_path = base_path+"/assets/"
        
        
        carscale = .9
        
        self.car = pygame.image.load(asset_path+"Car/carfull_nowheels.jpg").convert()
        self.car_rect = self.car.get_rect()
        scale = 600/self.car_rect.height*carscale*self.scale
        (self.car,self.car_rect) = scaleImage(self.car,scale)
        self.car_rect.center =  (np.array((700,365))*self.scale).astype(int)
        
        
        self.wheel = pygame.image.load(asset_path+"Car/singlewheel.png").convert_alpha()
        #self.Lwheel_rect = self.wheel.get_rect()
        #self.wheel = pygame.transform.smoothscale(self.wheel,(int(self.Lwheel_rect.width*scale33),int(self.Lwheel_rect.height*scale33)))
        #self.Lwheel_rect = self.wheel.get_rect()
        self.wheel,self.Lwheel_rect = scaleImage(self.wheel,carscale*self.scale)
        self.Lwheel_rect.center = (np.array(self.car_rect.topleft)+np.array((90,95))*carscale*self.scale).astype(int)
        self.Rwheel_rect = self.wheel.get_rect()
        self.Rwheel_rect.center = (np.array(self.car_rect.topright)+np.array((-75,95))*carscale*self.scale).astype(int)
        self.Lwheel_vec = np.array(self.Lwheel_rect.center)-np.array(self.car_rect.center)
        self.Rwheel_vec = np.array(self.Rwheel_rect.center)-np.array(self.car_rect.center)
        
        self.car_location = self.car_rect.center
        self.car_angle = 0
        self.wheel_angle = 0
        
        self.dwheel = pygame.image.load(asset_path+"Car/wheel.png").convert_alpha()
        #self.dwheel = pygame.transform.smoothscale(self.dwheel,(250,250))
        self.dwheel,self.dwheel_rect = scaleImage(self.dwheel,self.scale)
        self.dwheel_rect.center = (np.array([1200-135,800-135])*self.scale).astype(int)
        
        self.dwheel_dir = pygame.image.load(asset_path+"Car/wheeldir.png").convert_alpha()
        self.dwheel_dir,self.dwheel_dir_rect = scaleImage(self.dwheel_dir,self.scale)
        self.dwheel_dir_rect.center = self.dwheel_rect.center
        
        #self.light = Slider(asset_path+"Lab3/light.jpg",0,0,255,300)
        self.light = Slider(asset_path+"Lab3/light.jpg",val=0,output=(0,255),center=(300,800/2-100),size=400,axis=1,scale=self.scale)
        #self.manual = Slider(asset_path+"Lab3/manual_stain.jpg",0,0,500,100)
        self.manual = Slider(asset_path+"Lab3/manual_stain.jpg",val=0,output=(0,500),center=(100,800/2-100),size=400,axis=1,scale=self.scale)
        
        self.ranger = pygame.image.load(asset_path+"Lab3/ranger.jpg").convert()
        self.ranger,self.ranger_rect = scaleImage(self.ranger,self.scale/1.5)
        self.ranger_rect = self.ranger.get_rect()
        self.ranger_rect.centerx = int(200*self.scale)
        self.ranger_rect.centery = int(700*self.scale)

        self.compassrose = pygame.image.load(asset_path+"compassrose.png").convert_alpha()
        self.compassrose,self.compassrose_rect = scaleImage(self.compassrose,self.scale*carscale)
        self.compassrose_rect = self.compassrose.get_rect()
        self.compassrose_rect.center = self.car_rect.center
        
        self.flare1 = pygame.image.load(asset_path+"Car/flare1.png").convert_alpha()
        self.flare1,self.flare1_rect = scaleImage(self.flare1,self.scale)
        self.flare1_rect.center = (self.car_rect.centerx-int(5*self.scale),self.car_rect.centery+int(self.scale*50))
        self.flare2 = pygame.image.load(asset_path+"Car/flare2.png").convert_alpha()
        self.flare2,_ = scaleImage(self.flare2,self.scale)
        # flare 1 rect and flare 2 rect should be the same
        #self.flare2_rect = self.flare2.get_rect()
        #self.flare2_rect.center = self.flare1_rect.center
        self.flare_vec = np.array(self.flare1_rect.center)-np.array(self.car_rect.center)
        
        
        self.font = pygame.font.SysFont('Serif', 14)
        self.info = self.font.render(INFOB,True,(0,0,0))
        self.info_rect = self.info.get_rect()
        self.info_rect.bottomleft = (5,self.size[1])
        
        self.Servo = Servo(SIMSTEP)
        self.Drive = Drive(SIMSTEP)
        self.LED = LED(SIMSTEP)
        
        ss_path = asset_path + '/switch.png'
        self.SS = []
        self.SS.append(SlideSwitch(ss_path,0,
                                   center=(np.array([1145,25])*self.scale).astype(int),
                                   scale=self.scale,
                                   labels=True,
                                   title='P3.5',
                                   axis='x'))
        self.SS.append(SlideSwitch(ss_path,0,
                                   center=(np.array([1145,70])*self.scale).astype(int),
                                   scale=self.scale,
                                   labels=True,
                                   title='P3.6',
                                   axis='x'))
        self.SS.append(SlideSwitch(ss_path,0,
                                   center=(np.array([1145,115])*self.scale).astype(int),
                                   scale=self.scale,
                                   labels=True,
                                   title='P3.7',
                                   axis='x'))
        
        #Blit static things onto background (except compass rose since it's on top of car
        self.background.blit(self.ranger,self.ranger_rect)
        self.background.blit(self.info,self.info_rect)
        self.background.blit(self.dwheel_dir,self.dwheel_dir_rect)

        self.reset()
        
    def reset(self):
        self.car_angle = 0
        self.wheel_angle = 0
        self.turncar = False
        self.manual.hit = False
        self.light.hit = False
        
        self.rot_car = self.car.copy()
        self.rot_car_rect = self.car_rect.copy()
        
        self.rot_wheel = self.wheel.copy()
        self.rot_Lwheel_rect = self.Lwheel_rect.copy() 
        self.rot_Rwheel_rect = self.Rwheel_rect.copy()
        
        self.rot_dwheel = self.dwheel.copy()
        self.rot_dwheel_rect = self.dwheel_rect.copy()
        self.dwheel_angle = 0
        
        self.flare1.set_alpha(0)
        self.flare2.set_alpha(0)
        self.flare1_rect.center = self.car_rect.center
        
        self.light.setval(0)
        self.manual.setval(0)
        
        self.Servo.reset()
        self.Drive.reset()
        self.LED.reset()
        
        # Don't reset SlideSwitches, let state propogate
        #for SS in self.SS:
        #    SS.reset()
        
        
        if self.ctlmod:
            self.ctlmod.compass.setdirection(-self.car_angle)   # Game coordinates are inverted
            self.ctlmod.ranger.setecho(self.manual.output[1]-self.manual.val)
            self.ctlmod.ranger.setlight(self.light.val)
        
    def rotatecar(self):
        pos = pygame.mouse.get_pos()
        self.car_angle = (math.atan2(self.car_rect.centerx-pos[0],self.car_rect.centery-pos[1]))
        self.rot_car = pygame.transform.rotate(self.car,math.degrees(self.car_angle))
        self.rot_car_rect = self.rot_car.get_rect()
        self.rot_car_rect.center = self.car_rect.center
    
    def turnwheels(self, wheel_angle):
        self.wheel_angle = math.radians(wheel_angle)
        self.rot_wheel = pygame.transform.rotate(self.wheel,math.degrees(self.car_angle+self.wheel_angle))
        #self.rot_wheel = self.wheel.copy()
        self.rot_Lwheel_rect = self.rot_wheel.get_rect()
        self.rot_Rwheel_rect = self.rot_Lwheel_rect.copy()
        
        anglesin = np.sin(self.car_angle)
        anglecos = np.cos(self.car_angle)
        
        txmatrix = np.array([[anglecos,anglesin],[-anglesin,anglecos]])
        rot_Lwheel_vec = tuple(txmatrix.dot(self.Lwheel_vec)+np.array(self.car_rect.center))
        rot_Rwheel_vec = tuple(txmatrix.dot(self.Rwheel_vec)+np.array(self.car_rect.center))
        
        self.rot_Lwheel_rect.center = rot_Lwheel_vec
        self.rot_Rwheel_rect.center = rot_Rwheel_vec
        
        rot_flare_vec = tuple(txmatrix.dot(self.flare_vec)+np.array(self.car_rect.center))
        self.flare1_rect.center = rot_flare_vec
        
    def spinwheels(self):
        if abs(self.Drive.speed) > 0.1:  # Don't rotate on very low speeds
            self.dwheel_angle -= self.Drive.speed*17.6*SIMSTEP   # 17.6 is deg/s if speed = 1 cm.
            self.rot_dwheel = pygame.transform.rotate(self.dwheel,self.dwheel_angle)
            self.rot_dwheel_rect = self.rot_dwheel.get_rect()
            self.rot_dwheel_rect.center = self.dwheel_rect.center
        
    def setled(self):
        bright = self.LED.state
        if bright < 0.5:
            #self.flare2.set_alpha(0)
            self.flare1.set_alpha(2*bright*255)
        else:
            self.flare1.set_alpha(255)
        self.flare2.set_alpha(bright*255)
        
        
    def update(self):
        # Update peripheral timing
        self.ctlmod.timestep(SIMSTEP)
        
        # Update mechanical components
        self.Servo.setdc(self.ctlmod.xbr.getpin(0,4,'CCM'),self.ctlmod.pca0.Tperiod)
        self.Drive.setdc(self.ctlmod.xbr.getpin(0,5,'CCM'),self.ctlmod.pca0.Tperiod)
        self.LED.setdc(self.ctlmod.xbr.getpin(0,6,'CCM'),self.ctlmod.pca0.Tperiod)
        
        
        self.Servo.update()
        self.Drive.update()
        self.LED.update()
        
        for i,SS in enumerate(self.SS):
            self.ctlmod.xbr.setpin(3,5+i,SS.val)
    
    def run(self):
        while self.runctl > 0:
            if self.runctl >= 2:
                self.runctl.run = 1
                self.reset()
                
            self.update()
                
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    return
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    pos = pygame.mouse.get_pos()
                    if self.rot_car_rect.collidepoint(pos):
                        self.turncar = True
                    if self.manual.image_rect.collidepoint(pos):
                        self.manual.hit = True
                    if self.light.image_rect.collidepoint(pos):
                        self.light.hit = True
                    for SS in self.SS:
                        if SS.rect.collidepoint(pos):
                            SS.toggle()
                            
                elif event.type == pygame.MOUSEBUTTONUP:
                        self.turncar = False
                        self.manual.hit = False
                        self.light.hit = False
            
            if self.turncar:
                self.rotatecar()
                if self.ctlmod:
                    self.ctlmod.compass.setdirection(-self.car_angle)   # Game coordinates are inverted
            if self.manual.hit:
                self.manual.move()
                if self.ctlmod:
                    self.ctlmod.ranger.setecho(self.manual.output[1]-self.manual.val)
            if self.light.hit:
                self.light.move()
                if self.ctlmod:
                    self.ctlmod.ranger.setlight(self.light.val)
                    
            self.turnwheels(self.Servo.angle)
            self.spinwheels()
            self.setled()
                    
            self.screen.blit(self.background,(0,0))
            self.screen.blit(self.rot_car,self.rot_car_rect)
            self.screen.blit(self.flare1,self.flare1_rect)
            self.screen.blit(self.flare2,self.flare1_rect)
            self.screen.blit(self.rot_wheel,self.rot_Lwheel_rect)
            self.screen.blit(self.rot_wheel,self.rot_Rwheel_rect)
            self.screen.blit(self.rot_dwheel,self.rot_dwheel_rect)
            self.manual.draw(self.screen)
            self.light.draw(self.screen)
            for SS in self.SS:
                SS.draw(self.screen)
            #self.screen.blit(self.ranger,self.ranger_rect)
            self.screen.blit(self.compassrose,self.compassrose_rect)
            #self.screen.blit(self.info,self.info_rect)
            pygame.display.flip()
            
            self.clock.tick(1/SIMSTEP)
        
if __name__ == "__main__":
    sim = Simulation(0,1,'../assets/')
    sim.run()
        
        
        
