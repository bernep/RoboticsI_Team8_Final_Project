# Template: https://www.pygame.org/docs/tut/tom_games2.html
import pygame,math
import numpy as np
import sys,os
from labcommon import Gondola,ButtonBox # @UnresolvedImport
from version import SIMULATOR_VERSION
from _operator import pos

INFOA = "LITEC Lab 6 Simulator"
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
        self.screen = pygame.display.set_mode((1000,800))
        pygame.display.set_caption(INFOA)
        
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
        
        pygame.display.set_icon(pygame.image.load(asset_path+"icon.png"))
        
        self.gond = Gondola(asset_path,center=(600,400),simstep=SIMSTEP,sym=False)

        self.compassrose = pygame.image.load(asset_path+"compassrose.png").convert_alpha()
        self.compassrose_rect = self.compassrose.get_rect()
        self.compassrose_rect.center = self.gond.rect_gond.center
        
        self.target_pnts_orig = np.array([[0,0],[-352,-375]])
        self.target_pnts = self.target_pnts_orig
        self.heading_pnts_orig = np.array([[0,0],[-352,-352+23]])
        self.heading_pnts = self.heading_pnts_orig 
        
        self.font = pygame.font.SysFont('Serif', 14)
        self.info = self.font.render(INFOB,True,(0,0,0))
        self.info_rect = self.info.get_rect()
        self.info_rect.bottomleft = (5,800)
        
        # Control boxes
        self.info_font = pygame.font.SysFont('Serif', 20)
        self.boxes = []
        reset_box = ButtonBox()
        reset_box.text = self.info_font.render('RESTART',True,(0,0,0))
        reset_box.rect = pygame.Rect(5,5,250,40)
        reset_box.func = self.reset
        self.boxes.append(reset_box)
        start_box = ButtonBox()
        start_box.text = self.info_font.render('START ANGLE: {} deg'.format(self.gond.theta_orig/10),True,(0,0,0))
        start_box.rect = pygame.Rect(5,5+40+5,250,40)
        start_box.func = self.setangle
        self.boxes.append(start_box)
        spin_label = ButtonBox()
        spin_label.text = self.info_font.render('FORCE SPIN:',True,(0,0,0))
        spin_label.rect = pygame.Rect(5,5+40+5+40+5,205,30)
        spin_label.colordown = spin_label.color
        self.boxes.append(spin_label)
        spin_box = ButtonBox()
        spin_box.rect = pygame.Rect(5,5+40+5+40+5+30+5,100,100)
        spin_box.ico = pygame.transform.flip(pygame.image.load(asset_path+"Gondola/gondola_spin_ico.png").convert_alpha(),1,0)
        spin_box.ico_offset = np.array([0,-5])
        spin_box.func = self.spinleft
        self.boxes.append(spin_box)
        spin_box = ButtonBox()
        spin_box.rect = pygame.Rect(110,5+40+5+40+5+30+5,100,100)
        spin_box.ico = pygame.image.load(asset_path+"Gondola/gondola_spin_ico.png").convert_alpha()
        spin_box.ico_offset = np.array([0,-5])
        spin_box.func = self.spinright
        self.boxes.append(spin_box)
        
        self.reqblock = pygame.Surface((200,200)).convert()
        self.reqblock.fill((225,225,225))
        self.reqblock_rect = self.reqblock.get_rect()
        self.reqblock_rect.topleft = (5,500)
        self.reqblock.blit(self.info_font.render('Use These Fans:',True,(0,0,0)),(5,5))
        
        self.cfgdone = False
        
        self.des_heading = None

        self.reset()
        
    def reset(self,box=None):
        self.gond.reset()
        
    def setconfig(self,cfg):
        self.cfgdone = True
        # Things to generate:
        # a    Fans to use
        # b    Inertia of the gondola
        # c    Offset moment
        # d    desired heading
        #
        # x x x x x x x x
        # a a a b b b c c
        
        
        offset = 5+25
        
        self.reqblock = pygame.Surface((200,200)).convert()
        self.reqblock.fill((225,225,225))
        self.reqblock_rect = self.reqblock.get_rect()
        self.reqblock_rect.topleft = (5,500)
        self.reqblock.blit(self.info_font.render('Use These Fans:',True,(0,0,0)),(5,5))
        
        # get fans
        if cfg & 0xE0:
            if cfg & 0x80:
                self.reqblock.blit(self.info_font.render('RIGHT',True,(127,0,0)),(20,offset))
                offset += 25
            if cfg & 0x40:
                self.reqblock.blit(self.info_font.render('LEFT',True,(127,0,0)),(20,offset))
                offset += 25
            if cfg & 0x20:
                self.reqblock.blit(self.info_font.render('TAIL',True,(127,0,0)),(20,offset))
                offset += 25
        else:
            self.reqblock.blit(self.info_font.render('TAIL',True,(127,0,0)),(20,offset))
            offset += 25
        
        # get inertia
        scale = ((cfg >> 2) & 0x03) * (1-2*((cfg & 0x10) > 0))
        self.gond.I = 1+scale/10
                                    
        # get moment sign
        self.gond.Mo *= (1-2*((cfg & 0x01) > 0))
        
        # Desired heading
        tmp = ((cfg >> 4) ^ (cfg & 0x0F)) & 0x07
        self.des_heading = 45*tmp
        self.reqblock.blit(self.info_font.render('Use Desired Heading:',True,(0,0,0)),(5,offset))
        offset += 25
        self.reqblock.blit(self.info_font.render('{}\u00b0'.format(self.des_heading),True,(0,0,0)),(20,offset))
       
        anglesin = np.sin(np.radians(-self.des_heading))
        anglecos = np.cos(np.radians(-self.des_heading))
        txmatrix = np.array([[anglecos,anglesin],[-anglesin,anglecos]])
        self.target_pnts = txmatrix.dot(self.target_pnts_orig)
        
        
        
    def setangle(self,box):
        self.gond.theta_orig += 450
        self.gond.theta_orig %= 3600
        box.text = self.info_font.render('START ANGLE: {} deg'.format(self.gond.theta_orig/10),True,(0,0,0))
        
    def spinleft(self,box=None):
        self.gond.theta_t = -5000
    
    def spinright(self,box=None):
        self.gond.theta_t = 5000
        
    
    def update(self):
        self.ctlmod.timestep(SIMSTEP)
        
        for fan in self.gond.fans:
            fan.setdc(self.ctlmod.xbr.getpin(fan.port,fan.pin,'CCM'),self.ctlmod.pca0.Tperiod)
        
        self.gond.update()
        
        # Emit compass reading
        self.ctlmod.compass.setdirection(np.radians(self.gond.theta/10))
    
    def draw(self):
        self.screen.blit(self.background,(0,0))
        self.gond.draw(self.screen)
        for box in self.boxes:
            box.draw(self.screen)
        
        self.screen.blit(self.compassrose,self.compassrose_rect)
        
        pygame.draw.rect(self.screen,(245,245,245),self.info_rect.inflate(20,5))
        self.screen.blit(self.info,self.info_rect)
        
        font = pygame.font.SysFont('Serif',20)
        if self.des_heading is not None:
            error = self.des_heading - self.gond.theta/10
            if abs(error) <= 5:
                err_color = (0,150,0)
            else:
                err_color = (200,0,0)
            self.screen.blit(font.render("Error:",True,err_color),(5,700))
            txt = font.render("{:5.1f}\u00b0".format(error),True,err_color)
            self.screen.blit(txt,(175-txt.get_width(),700))
        self.screen.blit(font.render("Heading:",True,(0,0,0)),(5,725))
        txt = font.render("{:5.1f}\u00b0".format(self.gond.theta/10),True,(0,0,0))
        self.screen.blit(txt,(175-txt.get_width(),725))
        self.screen.blit(font.render("Velocity:",True,(0,0,0)),(5,750))
        txt = font.render("{:6.1f}\u00b0/s".format(self.gond.theta_t/10),True,(0,0,0))
        self.screen.blit(txt,(175-txt.get_width(),750))
        
        pygame.draw.line(self.screen,(0,100,255),self.target_pnts[:,0]+np.array(self.gond.rect_gond.center),self.target_pnts[:,1]+np.array(self.gond.rect_gond.center),width=5)
        anglesin = np.sin(np.radians(-self.gond.theta/10))
        anglecos = np.cos(np.radians(-self.gond.theta/10))
        txmatrix = np.array([[anglecos,anglesin],[-anglesin,anglecos]])
        self.heading_pnts = txmatrix.dot(self.heading_pnts_orig)
        pygame.draw.line(self.screen,(255,0,0),self.heading_pnts[:,0]+np.array(self.gond.rect_gond.center),self.heading_pnts[:,1]+np.array(self.gond.rect_gond.center),width=5)
        
        if self.reqblock is not None:
            self.screen.blit(self.reqblock,self.reqblock_rect)
        
        
        if not self.cfgdone:
            font = pygame.font.SysFont('Serif', 30,bold=True)
            endrect = pygame.Rect((0,0),(400,100))
            endrect.center = (600,400)
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
                    for box in self.boxes:
                        if box.rect.collidepoint(pos):
                            box.hit = True
                elif event.type == pygame.MOUSEBUTTONUP:
                    pos = pygame.mouse.get_pos()
                    for box in self.boxes:
                        if box.hit:
                            if box.rect.collidepoint(pos):
                                box.func(box)
                        box.hit = False
                    
            
            self.draw()
            pygame.display.flip()
            
            self.clock.tick(1/SIMSTEP)
        
if __name__ == "__main__":
    sim = Simulation(0,1,'../assets/')
    sim.run()
        
        
        
