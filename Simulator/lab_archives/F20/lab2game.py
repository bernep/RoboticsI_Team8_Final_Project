# Template: https://www.pygame.org/docs/tut/tom_games2.html
import pygame,math
import numpy as np
import sys,os
from labcommon import * # @UnresolvedImport
from version import SIMULATOR_VERSION

INFOA = "LITEC Lab 2 Simulator"
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
        self.size = (675,275)
        
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
        self.background = pygame.Surface(self.screen.get_size()).convert()
        self.background.fill((225,225,225))
        
        #############
        # Set up LEDs
        #############
        self.LEDA_off = pygame.image.load(asset_path+"Lab2/LEDg_off.png").convert_alpha()
        self.LEDA_off,LEDA_rect = scaleImage(self.LEDA_off,self.scale)
        self.LEDA_on = pygame.image.load(asset_path+"Lab2/LEDg_on.png").convert_alpha()
        self.LEDA_on,_ = scaleImage(self.LEDA_on,self.scale)
        self.LEDB_off = pygame.image.load(asset_path+"Lab2/LEDr_off.png").convert_alpha()
        self.LEDB_off,LEDB_rect = scaleImage(self.LEDB_off,self.scale)
        self.LEDB_on = pygame.image.load(asset_path+"Lab2/LEDr_on.png").convert_alpha()
        self.LEDB_on,_ = scaleImage(self.LEDB_on,self.scale)
        
        # Preset all locations
        LEDB_y = int((LEDB_rect.height/2+25)*self.scale)
        LEDA_y = int((LEDB_y+LEDB_rect.height/2+50)*self.scale)
        x_spacing = int((LEDB_rect.width+10)*self.scale)
        x_next = int(200*self.scale)
        self.LEDA_rects = []
        self.LEDB_rects = []
        for _ in range(8):
            self.LEDA_rects.append(self.LEDA_off.get_rect(center=(x_next,LEDA_y)))
            self.LEDB_rects.append(self.LEDB_off.get_rect(center=(x_next,LEDB_y)))
            x_next += x_spacing
            
        #LED values:
        self.LEDA = [0,0,0,0,0,0,0,0]
        self.LEDB = [0,0,0,0,0,0,0,0]
        
        ###############
        # Potentiometer
        ###############
        # Use the slider type
        POT = pygame.image.load(asset_path+"Lab2/pot_slider.png").convert_alpha()
        POT,_ = scaleImage(POT,self.scale)
        self.POT = Slider(image=POT,
                          output=(0,1000),
                          center=(int((self.LEDA_rects[-1].centerx-self.LEDA_rects[0].centerx)/2+self.LEDA_rects[0].centerx),int((LEDA_y+50+POT.get_rect().height/2)*self.scale)),
                          size=self.LEDA_rects[-1].centerx-self.LEDA_rects[0].centerx,
                          axis=0)
        self.POT_R = 10   # Resistor used with POT, in k
        # Put in slider background
        POT_BG = pygame.image.load(asset_path+"Lab2/pot_slider_bg.png").convert_alpha()
        POT_BG,POT_BG_RECT = scaleImage(POT_BG,self.scale)
        POT_BG_RECT.center = self.POT.center
        self.background.blit(POT_BG,POT_BG_RECT)
        
        ###############
        # Pushbuttons
        ###############
        self.PB1 = Pushbutton(asset_path+'/pb-unpressed.png',
                             asset_path+'/pb-pressed.png',
                             val=1,
                             center=(int(self.LEDA_rects[0].centerx/4),self.POT.center[1]),
                             scale=self.scale,
                             axis='y',
                             title='PB1')
        self.PB2 = Pushbutton(asset_path+'/pb-unpressed.png',
                             asset_path+'/pb-pressed.png',
                             val=1,
                             center=(int(2*self.LEDA_rects[0].centerx/3),self.POT.center[1]),
                             scale=self.scale,
                             axis='y',
                             title='PB2')
        
        
        ###############
        # Connections
        ###############
        self.ports = {'PB1':1,'PB2':1,'POT':1}
        self.pins = {'PB1':0,'PB2':0,'POT':0}
        
        
        self.font = pygame.font.SysFont('Serif', 14)
        self.info = self.font.render(INFOB,True,(0,0,0))
        self.info_rect = self.info.get_rect()
        self.info_rect.bottomleft = (5,self.size[1])
        
        pygame.draw.rect(self.background,(255,255,255),self.info_rect.inflate(10,5))
        self.background.blit(self.info,self.info_rect)
        
    def reset(self):
        pass

    def handle_key(self,eventkey):
        # get key pressed
        activekey = {pygame.K_1:self.PB1,pygame.K_KP1:self.PB1,pygame.K_2:self.PB2,pygame.K_KP2:self.PB2}.get(eventkey.key,'')
        if activekey:
            if eventkey.type == pygame.KEYDOWN:
                activekey.press()
            else:
                activekey.release()
                
    def update(self):
        if self.POT.hit:
            self.POT.move()
            
        # Emit ADC value
        pot_voltage = 5*10*self.POT.getratio()/(self.POT_R+10)
        self.ctlmod.xbr.setpin(self.ports['POT'],self.pins['POT'],pot_voltage)
        
        # Emit pushbutton states
        self.ctlmod.xbr.setpin(self.ports['PB1'],self.pins['PB1'],self.PB1.val)
        self.ctlmod.xbr.setpin(self.ports['PB2'],self.pins['PB2'],self.PB2.val)
        
        # Update peripheral timing
        self.ctlmod.timestep(SIMSTEP)
        
        # Get LED values
        p2 = self.ctlmod.gpio.getport_out(2)
        p3 = self.ctlmod.gpio.getport_out(3)
        for i in range(8):
            self.LEDA[i] = (p2 >> (7-i)) & 0x01
            self.LEDB[i] = (p3 >> (7-i)) & 0x01
        
    def setconfig(self,cfg):
        # clear pins
        for key in self.pins.keys():
            self.pins[key] = 8
        
        for i,key in enumerate(self.pins.keys()):
            tmp = (cfg >> i) % 8
            while tmp in self.pins.values():
                tmp += 1
                if tmp == 8:
                    tmp = 0
            self.pins[key] = tmp
            
        # get POT R
        self.POT_R = {0:0.420,1:11,2:32,3:73}[(cfg>>4)%4]
        potR_text = {.42:"420 Ω",11:"11 kΩ",32:"32 kΩ",73:"73 kΩ"}[self.POT_R]
            
        #Place instructions
        _loc = (np.array([80,80])*self.scale).astype(int)
        font = pygame.font.SysFont('Serif', 18)
        textA = font.render("PB1 - P1.{}".format(self.pins['PB1']),True,(0,0,0))
        textB = font.render("PB2 - P1.{}".format(self.pins['PB2']),True,(0,0,0))
        textC = font.render("POT - P1.{}".format(self.pins['POT']),True,(0,0,0))
        textD = font.render("R1 - {}".format(potR_text),True,(0,0,0))
        text_height = textA.get_height()
        text_width = max(textA.get_width(),textB.get_width(),textC.get_width(),textD.get_width())
        bg_rect = pygame.Rect((0,0),(np.array([text_width+20,4*text_height+20])*self.scale).astype(int))
        bg_rect.center = _loc
        pygame.draw.rect(self.background,(255,255,255),bg_rect)
        pygame.draw.rect(self.background,(0,0,0),bg_rect,width=2)
        self.background.blit(textA,textA.get_rect(center=_loc+np.array([0,-3*text_height/2])))
        self.background.blit(textB,textB.get_rect(center=_loc+np.array([0,-text_height/2])))
        self.background.blit(textC,textC.get_rect(center=_loc+np.array([0,+text_height/2])))
        self.background.blit(textD,textD.get_rect(center=_loc+np.array([0,+3*text_height/2])))
            
        self.cfgdone = True
        
    def blit(self):
        self.screen.blit(self.background,(0,0))
        
        # Draw all LEDS
        for led,rect in zip(self.LEDA,self.LEDA_rects):
            if led:
                self.screen.blit(self.LEDA_off,rect)
            else:
                self.screen.blit(self.LEDA_on,rect)
        for led,rect in zip(self.LEDB,self.LEDB_rects):
            if led:
                self.screen.blit(self.LEDB_off,rect)
            else:
                self.screen.blit(self.LEDB_on,rect)
        
        self.POT.draw(self.screen)
        
        self.PB1.draw(self.screen)
        self.PB2.draw(self.screen)
            
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
                    pos = pygame.mouse.get_pos()
                    if self.POT.hit:
                        self.POT.hit = False
                    elif self.POT.checkClick(pos):
                        self.POT.hit = not self.POT.hit
                elif event.type == pygame.MOUSEBUTTONUP:
                    pass
                elif event.type in [pygame.KEYUP,pygame.KEYDOWN]:
                    self.handle_key(event)
                    
                    
            self.blit()
                
            pygame.display.update()

            self.clock.tick(1/SIMSTEP)
                
            
        
if __name__ == "__main__":
    sim = Simulation(0,1,'../assets/')
    sim.run()
        
        
        
