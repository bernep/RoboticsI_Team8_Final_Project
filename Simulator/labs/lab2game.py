# Template: https://www.pygame.org/docs/tut/tom_games2.html
import pygame,math
import numpy as np
import sys,os
from labcommon import * # @UnresolvedImport
from version import SIMULATOR_VERSION

INFOA = "LITEC Lab 2 Simulator"
INFOB = INFOA+" Version "+SIMULATOR_VERSION

SIMSTEP = 0.01 # seconds between updates

class Asteroid():
    x = 0;
    y = 0;
    life = 0;
    rect = 0;

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
        self.size = (555+355,355)
        
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
        
        ###############
        # Potentiometers
        ###############
        # Use the slider type
        pot_center = (160+55/2,120+55/2)
        pot_size = 255
        pot_scale = 0.5
        POT = pygame.image.load(asset_path+"Lab2/pot_slider.png").convert_alpha()
        POT,_ = scaleImage(POT,self.scale*pot_scale)
        self.POTX = Slider(image=POT,
                          output=(0,1000),
                          center=(np.array([pot_center[0],pot_center[1]+pot_size/2+25+10])).astype(int),
                          size=pot_size,
                          axis=0)
        self.POTY = Slider(image=pygame.transform.rotozoom(POT,90,1),
                          output=(0,1000),
                          center=(np.array([pot_center[0]-pot_size/2-25-10,pot_center[1]])).astype(int),
                          size=pot_size,
                          axis=1)
        self.POT_R = 10   # Resistor used with POT, in k
        # Put in slider background
        POT_BG = pygame.image.load(asset_path+"Lab2/pot_slider_bg_255.png").convert_alpha()
        POT_BG,POT_BG_RECT = scaleImage(POT_BG,self.scale)
        POT_BG_RECT.center = self.POTX.center
        self.background.blit(POT_BG,POT_BG_RECT)
        #POT_BG = pygame.transform.rotozoom(POT_BG,90,1)
        POT_BG = pygame.transform.rotate(POT_BG,90)
        POT_BG_RECT = POT_BG.get_rect(center = self.POTY.center)
        self.background.blit(POT_BG,POT_BG_RECT)

        
        # Create joystick rectange
        self.reticle_size = 20
        self.JS = pygame.Rect(((np.array(pot_center)-np.array([pot_size+self.reticle_size,pot_size+self.reticle_size])/2)*self.scale).astype(int),(np.array([pot_size+self.reticle_size,pot_size+self.reticle_size])*self.scale).astype(int))
        self.JS_reticle = pygame.Surface((np.array([20,20])).astype(int)).convert()
        self.JS_reticle.fill((255,255,255))
        self.JS_reticle_rect = self.JS_reticle.get_rect()
        pygame.draw.line(self.JS_reticle,(0,0,0),(self.JS_reticle_rect.centerx-1,self.JS_reticle_rect.top),(self.JS_reticle_rect.centerx-1,self.JS_reticle_rect.bottom),width=2)
        pygame.draw.line(self.JS_reticle,(0,0,0),(self.JS_reticle_rect.left,self.JS_reticle_rect.centery-1),(self.JS_reticle_rect.right,self.JS_reticle_rect.centery-1),width=2)
        pygame.draw.circle(self.JS_reticle,(0,0,0),self.JS_reticle_rect.center,int(self.JS_reticle_rect.width*2/6),width=1)
        self.JS_reticle_rect.center = self.JS.center


        self.JS_hit = False
        self.JS_loc = np.array([pot_center,pot_center])*self.scale
        
        
        ###############
        # Pushbuttons
        ###############
        self.PB1 = Pushbutton(asset_path+'/pb-unpressed.png',
                             asset_path+'/pb-pressed.png',
                             val=1,
                             center=(np.array(self.JS.topright) + np.array([35,30])*self.scale).astype(int),
                             scale=self.scale*.75,
                             axis='y',
                             title='PB1')
        self.PB2 = Pushbutton(asset_path+'/pb-unpressed.png',
                             asset_path+'/pb-pressed.png',
                             val=1,
                             center=(np.array(self.JS.topright) + np.array([35,30])*self.scale + np.array([self.PB1.rect.width*3/2,0])).astype(int),
                             scale=self.scale*.75,
                             axis='y',
                             title='PB2')
        
        #############
        # Set up LEDs
        #############
        LED_scale = 0.5
        self.LEDG_off = pygame.image.load(asset_path+"Lab2/LEDg_off.png").convert_alpha()
        self.LEDG_off,LEDG_rect = scaleImage(self.LEDG_off,self.scale*LED_scale)
        self.LEDG_on = pygame.image.load(asset_path+"Lab2/LEDg_on.png").convert_alpha()
        self.LEDG_on,_ = scaleImage(self.LEDG_on,self.scale*LED_scale)
        self.LEDR_off = pygame.image.load(asset_path+"Lab2/LEDr_off.png").convert_alpha()
        self.LEDR_off,LEDR_rect = scaleImage(self.LEDR_off,self.scale*LED_scale)
        self.LEDR_on = pygame.image.load(asset_path+"Lab2/LEDr_on.png").convert_alpha()
        self.LEDR_on,_ = scaleImage(self.LEDR_on,self.scale*LED_scale)
        
        # Place the Life LEDs
        LEDL_x = self.JS.right + 35
        #LEDL_x = int(self.size[0]-LEDG_rect.width)
        y_spacing = int((LEDG_rect.width+7))
        y_next = self.JS.top + 30 + 50
        self.LEDL_rects = []
        for _ in range(8):
            self.LEDL_rects.append(self.LEDG_off.get_rect(center=(LEDL_x,y_next)))
            y_next += y_spacing
            
        #LED values:
        self.LEDL = [0,0,0,0,0,0,0,0]
        
        ###############
        # Connections
        ###############
        self.ports = {'PB1':1,'PB2':1,'POTX':1,'POTY':1}
        self.pins = {'PB1':0,'PB2':0,'POTX':0,'POTY':1}
        
        
        ###############
        # Play Window
        ###############
        self.asteroids = []
        self.lifetime = [0,0,0]
        self.world_base = pygame.Surface((300,300)).convert()
        self.world_base.fill((0,0,0))
        self.world_rect = self.world_base.get_rect()
        self.world_rect.bottomright = np.array(self.size) - np.array((25,25))
        self.asteroid_surf = pygame.Surface((9,9), pygame.SRCALPHA).convert_alpha()
        self.asteroid_rect = self.asteroid_surf.get_rect()
        self.asteroid_small = self.asteroid_surf.copy()
        pygame.draw.circle(self.asteroid_small,(255,255,255),(5,5),2)
        self.asteroid_med = self.asteroid_surf.copy()
        pygame.draw.circle(self.asteroid_med,(255,255,255),(5,5),3)
        self.asteroid_big = self.asteroid_surf.copy()
        pygame.draw.circle(self.asteroid_big,(255,255,255),(5,5),4)
        self.asteroid_crash = self.asteroid_surf.copy()
        pygame.draw.circle(self.asteroid_crash,(255,0,0),(5,5),4)
        self.asteroid_hit = self.asteroid_surf.copy()
        pygame.draw.circle(self.asteroid_hit,(255,255,255),(5,5),4,width=1)
        self.w_reticle = pygame.Surface((12,12), pygame.SRCALPHA).convert_alpha()
        self.w_reticle_rect = self.w_reticle.get_rect()
        pygame.draw.lines(self.w_reticle,(255,255,0),False,((0,4),(0,0),(4,0)))
        pygame.draw.lines(self.w_reticle,(255,255,0),False,((0,8),(0,11),(4,11)))
        pygame.draw.lines(self.w_reticle,(255,255,0),False,((8,11),(11,11),(11,8)))
        pygame.draw.lines(self.w_reticle,(255,255,0),False,((8,0),(11,0),(11,4)))
        self.world = self.world_base.copy()
        self.world.blit(self.w_reticle,(150,150))
        



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
        pass
        activekey = {pygame.K_1:self.PB1,pygame.K_KP1:self.PB1,pygame.K_2:self.PB2,pygame.K_KP2:self.PB2}.get(eventkey.key,'')
        if activekey:
            if eventkey.type == pygame.KEYDOWN:
                activekey.press()
            else:
                activekey.release()
        elif eventkey.key == pygame.K_ESCAPE:
            pygame.mouse.set_visible(True)
            pygame.event.set_grab(False)
            self.JS_hit = False
            self.PB1.release()

    def handle_mouse(self,eventmouse):
        if self.JS_hit:
            if eventmouse.button == 1:
                if eventmouse.type == pygame.MOUSEBUTTONDOWN:
                    self.PB1.press()
                else:
                    self.PB1.release()
            elif eventmouse.button == 3:
                pygame.mouse.set_visible(True)
                pygame.event.set_grab(False)
                self.JS_hit = False
                self.PB1.release()
        elif eventmouse.type == pygame.MOUSEBUTTONDOWN:
            pos = pygame.mouse.get_pos()
            if self.POTX.hit:
                self.POTX.hit = False
            elif self.POTY.hit:
                self.POTY.hit = False
                pygame.event.set_grab(False)
                pygame.mouse.set_visible(True)
            elif self.POTX.checkClick(pos):
                self.POTX.hit = not self.POTX.hit
            elif self.POTY.checkClick(pos):
                self.POTY.hit = not self.POTY.hit
            elif self.JS.collidepoint(pos):
                self.JS_hit = True
                self.JS_loc = np.array(pos)
                pygame.mouse.set_visible(False)
                pygame.event.set_grab(True)
                pygame.mouse.get_rel()

        elif eventmouse.type == pygame.MOUSEBUTTONUP:
            pass


                
    def update(self):
        if self.POTX.hit:
            self.POTX.move()
        if self.POTY.hit:
            self.POTY.move()

        if self.JS_hit:
            JS_loc = np.array(self.JS_reticle_rect.center).astype('float64')
            r_w = self.JS_reticle_rect.width/2
            
            JS_loc += np.array(pygame.mouse.get_rel()).astype('float64')
            if JS_loc[0] < self.JS.left+r_w:
                JS_loc[0] = self.JS.left+r_w
            elif JS_loc[0] > self.JS.right-r_w:
                JS_loc[0] = self.JS.right-r_w
            if JS_loc[1] < self.JS.top+r_w:
                JS_loc[1] = self.JS.top+r_w
            elif JS_loc[1] > self.JS.bottom-r_w:
                JS_loc[1] = self.JS.bottom-r_w
            self.JS_reticle_rect.center = JS_loc.astype(int)
            self.POTX.move(JS_loc)
            self.POTY.move(JS_loc)
            
        # Emit ADC value
        potx_voltage = 5*10*self.POTX.getratio()/(self.POT_R+10)
        poty_voltage = 5*10*self.POTY.getratio()/(self.POT_R+10)
        self.ctlmod.xbr.setpin(self.ports['POTX'],self.pins['POTX'],potx_voltage)
        self.ctlmod.xbr.setpin(self.ports['POTY'],self.pins['POTY'],poty_voltage)
        
        # Emit pushbutton states
        self.ctlmod.xbr.setpin(self.ports['PB1'],self.pins['PB1'],self.PB1.val)
        self.ctlmod.xbr.setpin(self.ports['PB2'],self.pins['PB2'],self.PB2.val)
        
        # Update peripheral timing
        self.ctlmod.timestep(SIMSTEP)
        
        # Get LED values
        p3 = self.ctlmod.gpio.getport_out(3)
        for i in range(8):
            self.LEDL[i] = (p3 >> (7-i)) & 0x01
        
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
        _loc = (np.array([460,250])*self.scale).astype(int)
        font = pygame.font.SysFont('Serif', 18)
        textA = font.render("PB1 - P1.{}".format(self.pins['PB1']),True,(0,0,0))
        textB = font.render("PB2 - P1.{}".format(self.pins['PB2']),True,(0,0,0))
        textC = font.render("POT_x - P1.{}".format(self.pins['POTX']),True,(0,0,0))
        textD = font.render("POT_y - P1.{}".format(self.pins['POTY']),True,(0,0,0))
        textE = font.render("R1 - {}".format(potR_text),True,(0,0,0))
        text_height = textA.get_height()
        text_width = max(textA.get_width(),textB.get_width(),textC.get_width(),textD.get_width())
        bg_rect = pygame.Rect((0,0),(np.array([text_width+20,5*text_height+20])*self.scale).astype(int))
        bg_rect.center = _loc
        pygame.draw.rect(self.background,(255,255,255),bg_rect)
        pygame.draw.rect(self.background,(0,0,0),bg_rect,width=2)
        self.background.blit(textA,textA.get_rect(center=_loc+np.array([0,-4*text_height/2])))
        self.background.blit(textB,textB.get_rect(center=_loc+np.array([0,-2*text_height/2])))
        self.background.blit(textC,textC.get_rect(center=_loc+np.array([0,0])))#+text_height/2])))
        self.background.blit(textD,textD.get_rect(center=_loc+np.array([0,+2*text_height/2])))
        self.background.blit(textE,textE.get_rect(center=_loc+np.array([0,+4*text_height/2])))
            
        self.cfgdone = True
        
    def blit(self):
        self.screen.blit(self.background,(0,0))
        
        # Draw all LEDS
        for led,rect in zip(self.LEDL,self.LEDL_rects):
            if led:
                self.screen.blit(self.LEDG_off,rect)
            else:
                self.screen.blit(self.LEDG_on,rect)
        
        self.POTX.draw(self.screen)
        self.POTY.draw(self.screen)

        pygame.draw.rect(self.screen,(255,255,255),self.JS)
        if self.JS_hit:
            self.screen.blit(self.JS_reticle,self.JS_reticle_rect)
        
        self.PB1.draw(self.screen)
        self.PB2.draw(self.screen)

        self.world_update()
        self.background.blit(self.world,self.world_rect)
            
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
        
    def world_update(self):
        while self.ctlmod.aux.in_buffer:
            cmd = self.ctlmod.aux.get_next()
            if cmd:
                if cmd[0] == 1:
                    self.lifetime = cmd[1:4]
                    self.asteroids = []
                    self.world = self.world_base.copy()
                elif cmd[0] == 2:
                    self.world = self.world_base.copy()
                    crashes = []
                    for i,_ in enumerate(self.asteroids):
                        self.asteroids[i].life -= 1
                        if self.asteroids[i].life >= self.lifetime[1]:
                            self.world.blit(self.asteroid_small,self.asteroids[i].rect)
                        elif self.asteroids[i].life >= self.lifetime[2]:
                            self.world.blit(self.asteroid_med,self.asteroids[i].rect)
                        elif self.asteroids[i].life != 0: 
                            self.world.blit(self.asteroid_big,self.asteroids[i].rect)
                        else:
                            self.world.blit(self.asteroid_crash,self.asteroids[i].rect)
                            crashes.append(i)
                    for crash in crashes:
                        self.asteroids.pop(crash)
                    self.w_reticle_rect.center = (int(3.75*cmd[1]),int(3.75*cmd[2]))
                    self.world.blit(self.w_reticle,self.w_reticle_rect)
                elif cmd[0] == 4:
                    self.asteroids.append(Asteroid())
                    self.asteroids[-1].x = cmd[1]
                    self.asteroids[-1].y = cmd[2]
                    self.asteroids[-1].life = self.lifetime[0]
                    self.asteroids[-1].rect = self.asteroid_rect.copy()
                    self.asteroids[-1].rect.center = (int(3.75*cmd[1]),int(3.75*cmd[2]))
                elif cmd[0] == 5:
                    found = False
                    for i,_ in enumerate(self.asteroids):
                        if self.asteroids[i].x == cmd[1]:
                            if self.asteroids[i].y == cmd[2]:
                                self.world.blit(self.asteroid_hit,self.asteroids[i].rect)
                                found = True
                                break
                    if found:
                        self.asteroids.pop(i)

            
    def run(self):
        try:
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
                    elif event.type in [pygame.MOUSEBUTTONDOWN,pygame.MOUSEBUTTONUP]:
                        self.handle_mouse(event)
                    elif event.type in [pygame.KEYUP,pygame.KEYDOWN]:
                        self.handle_key(event)
                       
                        
                self.blit()
                    
                pygame.display.update()

                self.clock.tick(1/SIMSTEP)
        finally:
            pygame.quit()
                
            
        
if __name__ == "__main__":
    sim = Simulation(0,1,'../assets/')
    sim.run()
        
        
        
