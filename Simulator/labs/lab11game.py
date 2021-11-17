# Template: https://www.pygame.org/docs/tut/tom_games2.html
import pygame,math
import numpy as np
import sys,os
from labcommon import * # @UnresolvedImport
from version import SIMULATOR_VERSION

INFOA = "LITEC Lab 1.1 Simulator"
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
        
        # Get file locations
        if asset_path is None:
            try:
                base_path = sys._MEIPASS
            except Exception:
                base_path = os.path.abspath(".")
            asset_path = base_path+"/assets/"
            
        
        #self.size = self.background.get_rect().size
        self.size = (1000,942)
        
        # Ensure that display is large enough to show game window, if not, shrink
        dispsize = pygame.display.Info()
        self.scale = min(dispsize.current_w*0.95/self.size[0],dispsize.current_h*0.9/self.size[1])
        if self.scale >= 1:
            self.scale = 1
        else:
            self.size = tuple((np.array(self.size)*self.scale).astype(int))
            
        
            
        # Initialize the screen
        self.screen = pygame.display.set_mode(self.size)
        pygame.display.set_caption(INFOA)
        pygame.display.set_icon(pygame.image.load(asset_path+"icon.png"))
       
        # Get base image
        self.background = pygame.image.load(asset_path+"Lab11/base.jpg").convert()
        self.background,self.bg_rect = scaleImage(self.background,self.scale)
        
        
        # Load all the other pictures
        self.pics = {}
        self.rects = {}
        self.pics["SS"] = pygame.image.load(asset_path+"Lab11/SS.png").convert_alpha()
        self.rects["SS"] = pygame.Rect((np.array([256,138])*self.scale).astype(int),(np.array([50,88])*self.scale).astype(int))
        self.pics["PB1"] = pygame.image.load(asset_path+"Lab11/finger1.png").convert_alpha()
        self.rects["PB1"] = pygame.Rect((np.array([270,327])*self.scale).astype(int),(np.array([35,35])*self.scale).astype(int))
        self.pics["PB2"] = pygame.image.load(asset_path+"Lab11/finger2.png").convert_alpha()
        self.rects["PB2"] = pygame.Rect((np.array([502,190])*self.scale).astype(int),(np.array([35,35])*self.scale).astype(int))
        self.pics["LED"] = pygame.image.load(asset_path+"Lab11/LED.png").convert_alpha()
        self.rects["LED"] = self.bg_rect
        self.pics["BLEDg"] = pygame.image.load(asset_path+"Lab11/BLED_Green.png").convert_alpha()
        self.rects["BLEDg"] = self.bg_rect
        self.pics["BLEDr"] = pygame.image.load(asset_path+"Lab11/BLED_Red.png").convert_alpha()
        self.rects["BLEDr"] = self.bg_rect
        self.pics["gear"] = pygame.image.load(asset_path+"Lab11/gear_center.png").convert_alpha()
        if self.scale < 1:
            for key in self.pics.keys():
                self.pics[key],_ = scaleImage(self.pics[key],self.scale) 
        # Gear is the only image that isn't the full screen, need to assign center location
        self.rects["gear"] = self.pics["gear"].get_rect()
        self.rects["gear"].center = (np.array([521,740])*self.scale).astype(int)
        self.gear_angle = 0 # Keep track of rotation of the gear
        self.gear_speed = 10 # Degrees per frame
        self.gear_rot = self.pics["gear"]
        self.gear_rot_rect = self.rects["gear"]
        
        # A bunch of dictionarys describing the connections
        self.port = {}
        self.pin = {}
        self.io = {}
        self.ihit = {}  # Only applicable for inputs (mouse is down on it)
        self.ihold = {}  # Only applicable for pushbuttons
        self.state = {} 
        for key in self.pics.keys():
            self.port[key] = 0
            self.pin[key] = 0
            if key in ["SS","PB1","PB2"]:
                self.io[key] = "INPUT"
            else:
                self.io[key] = "OUTPUT"
            self.ihit[key] = False
            self.ihold[key] = False
            self.state[key] = False
       
        self.font = pygame.font.SysFont('Serif', 14)
        self.info = self.font.render(INFOB,True,(0,0,0))
        self.info_rect = self.info.get_rect()
        self.info_rect.bottomleft = (5,self.size[1])
    
    def reset(self):
        for key in self.pics.keys():
            self.ihit[key] = False
            self.ihold[key] = False
            self.state[key] = False
        
    def update(self):
        # Update peripheral timing # Not needed in this program
        self.ctlmod.timestep(SIMSTEP)
        
        # Emit switch values and read output values
        for key in self.pics.keys():
            if self.io[key] == "INPUT":
                self.ctlmod.xbr.setpin(self.port[key],self.pin[key],not self.state[key])
            else:
                self.state[key] = not self.ctlmod.xbr.getpin(self.port[key],self.pin[key],"GPIO")
        
    def setconfig(self,cfg):
        # Port and pins for SS, PB1, PB2, BLEDr, BLEDg, gear
        #    
        generated = []
        count = 0
        for key in self.port.keys():
            self.port[key] = ((cfg>>count) % 2) + 2 # Get port in 2 or 3
            self.pin[key] = ((cfg>>count) % 8)      # Get pin in 0-7
            gen_tmp = self.port[key]*10+self.pin[key]
            while gen_tmp in generated:
                self.pin[key] += 1
                self.pin[key] %= 8
                gen_tmp = self.port[key]*10+self.pin[key]
            generated.append(gen_tmp)
            count += 1
            
        # Generate text for each IO and place onto background
        _locs = [(118,190),(118,310),(465,72),(118,417),(910,409),(910,550),(118,495)]
        font = pygame.font.SysFont('Serif', 18)
        for i,key in enumerate(self.port.keys()):
            _loc = (np.array(_locs[i])*self.scale).astype(int) 
            text = font.render("P{}.{}".format(self.port[key],self.pin[key]),True,(0,0,0))
            text_rect = text.get_rect()
            text_rect.center = _loc
            _bg = text_rect.inflate(10,5)
            pygame.draw.rect(self.background,(225,225,255),_bg)#,border_radius=10)
            pygame.draw.rect(self.background,(0,0,0),_bg,width=2)#,border_radius=10)
            self.background.blit(text,text_rect)
        
        self.cfgdone = True
        
    def mouse_down(self):
        pos = pygame.mouse.get_pos()
        buttons = pygame.mouse.get_pressed()
        for key in self.rects.keys():
            if self.io[key] == "OUTPUT":
                continue
            if self.rects[key].collidepoint(pos):
                if key.startswith("PB"):
                    if buttons[2]:
                        self.ihold[key] = not self.ihold[key]
                        if self.ihold[key]:
                            self.state[key] = True
                        else:
                            self.state[key] = False
                    else:
                        self.state[key] = True
                else:
                    self.state[key] = not self.state[key]
    
    def mouse_up(self):
        for key in self.rects.keys():
            if key.startswith("PB"):
                if not self.ihold[key]:
                    self.state[key] = False
                    
    def handle_key(self,eventkey):
        # get key pressed
        activekey = {pygame.K_1:"1",pygame.K_KP1:"1",pygame.K_2:"2",pygame.K_KP2:"2"}.get(eventkey.key,'')
        if activekey:
            pb_pressed = "PB" + activekey
            if eventkey.type == pygame.KEYDOWN:
                self.ihold[pb_pressed] = True
                self.state[pb_pressed] = True
            else:
                self.ihold[pb_pressed] = False 
                self.state[pb_pressed] = False
        elif (eventkey.key == pygame.K_3) or (eventkey.key == pygame.K_KP3):
            if eventkey.type == pygame.KEYDOWN:
                self.state["SS"] = not self.state["SS"]
        
        
        
        
    def blit(self):
        self.screen.blit(self.background,(0,0))
        
        for key in self.state.keys():
            if self.state[key]:
                if key == 'gear':
                    self.gear_angle += self.gear_speed
                    self.gear_rot = pygame.transform.rotate(self.pics[key],self.gear_angle)
                    self.gear_rot_rect = self.gear_rot.get_rect(center=self.rects[key].center)
                elif key in ['BLEDg','BLEDr']:
                    continue
                else:
                    self.screen.blit(self.pics[key],self.bg_rect)
        # Always blit the gear
        self.screen.blit(self.gear_rot,self.gear_rot_rect)
        # Check state of BLED outputs
        if self.state['BLEDg'] != self.state['BLEDr']:
            if self.state['BLEDg']:
                self.screen.blit(self.pics['BLEDg'],self.bg_rect)
            else:
                self.screen.blit(self.pics['BLEDr'],self.bg_rect)
            
        self.screen.blit(self.info,self.info_rect)
        
        font = pygame.font.SysFont('Serif', 30,bold=True)
        if not self.cfgdone:
            endrect = pygame.Rect((0,0),(400,100))
            endrect.center = (int(self.size[0]/2),int(self.size[1]/2))
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
                    self.mouse_down()
                elif event.type == pygame.MOUSEBUTTONUP:
                    self.mouse_up()
                elif event.type in [pygame.KEYUP,pygame.KEYDOWN]:
                    self.handle_key(event) 
                    
            self.blit()
                
            pygame.display.update()

            self.clock.tick(1/SIMSTEP)
                
            
        
if __name__ == "__main__":
    sim = Simulation(0,1,'../assets/')
    sim.run()
        
        
        
