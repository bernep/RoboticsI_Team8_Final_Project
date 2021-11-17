import pygame,math
import numpy as np
import sys,os
from labcommon import * # @UnresolvedImport
from version import SIMULATOR_VERSION
from random import randint

INFOA = "LITEC Lab 4 Simulator"
INFOB = INFOA+" Version "+SIMULATOR_VERSION

SIMSTEP = 0.01 # seconds between updates

class Wall():
    wall = 0
    wall_rect = 0
    _width = 1
    _thick = 1
    opening = 1
    def __init__(self,center):
        self.center = np.array(center,dtype='float64')
        self.rect = Wall.wall_rect.copy()
        self.rect.center = self.center
    
    # This doesn't seem to work as cls.objects doesn't exist.
    #@classmethod
    #def move_all(cls,delta):
    #    for obj in cls.objects:
    #        obj.center -= delta
    
    def move(self,delta):
        self.center[1] -= delta
        #print(self.center)
        self.rect.center = self.center.astype(int)
    
    @classmethod
    def create_wall(cls,window_width,opening_width,thickness,scale):
        cls._width = window_width*3
        cls.wall = pygame.Surface((cls._width,int(thickness*scale)),pygame.SRCALPHA,32).convert_alpha()
        cls.wall_rect = cls.wall.get_rect()
        cls._thick = int(thickness*scale) 
        cls.opening = int(opening_width*scale/2)
        pygame.draw.line(cls.wall,(0,0,0),cls.wall_rect.midleft,(cls.wall_rect.centerx-cls.opening,cls.wall_rect.centery),width=cls._thick)
        pygame.draw.line(cls.wall,(0,0,0),cls.wall_rect.midright,(cls.wall_rect.centerx+cls.opening,cls.wall_rect.centery),width=cls._thick)
    
    def blit(self,surf):
        surf.blit(Wall.wall,self.rect)
        

class Simulation():
    def __init__(self,controlmodel,runctl,asset_path=None):
        self.ctlmod = controlmodel
        self.runctl = runctl
        self.cfgdone = False
        # Initialize screen
        pygame.init()
        pygame.font.init()
        self.clock = pygame.time.Clock()
        
        self.size = np.array((1200,600))
        
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
        #self.background = pygame.Surface(self.screen.get_size()).convert()
        #self.background.fill((225,225,225))
        
        # Create wall template
        Wall.create_wall(self.size[0],250,10,self.scale)
        self.walls = []
        self.wall_loc = 0  # Index of location of car between walls.  E.g., if wall_loc is 5, then car is between wall 4 and wall 5
        self.wall_spacing = 400
        self.wall_range = (Wall.opening,self.size[0]-Wall.opening)
        self.col_points = np.array([[np.nan,np.nan],[np.nan,np.nan],[np.nan,np.nan],[np.nan,np.nan]])
        self.lwall = pygame.Rect(0,0,1,self.size[1])
        self.lwall.topright = (0,0)
        self.rwall = self.lwall.copy()
        self.rwall.topleft = (self.size[0],0)
        
        
        self.car = DrivingCar(asset_path,
                              scale=0.08*self.scale,
                              center=scaleCoord((self.size[0]/2,self.size[1]/4*3),self.scale),
                              angle=180,
                              simstep=SIMSTEP)
        self.car_base = self.car.rect_car.copy()
        self.car_base.center = (0,0)
        
        # Set scaling of speed
        self.car.Drive.maxspeed *=self.scale*1.25
        self.car.start_speed *= self.scale*1.25
        self.car.dead_speed *= self.scale*1.25
        self.car.Drive.maxchange *= self.scale*1.25
        self.car_defaults = [self.car.Drive.maxspeed,self.car.Drive.maxchange,self.car.start_speed,self.car.dead_speed]
        
        self.crash = False
        
        
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
        
        # Don't use ranger within the car object as it's only for 1. Set up calculations for all 3 here
        # Car is always going to be centered:
        # Negative on the y to make the angles CCW in the window, not CW
        self.rangers = np.array([np.array([0,self.car.rect_car.height/2]),
                        np.array([-self.car.rect_car.width/2,0]),
                        np.array([self.car.rect_car.width/2,0])])
        # self.ranger_angles = [np.radians(90),np.radians(180),np.radians(0)]
        self.ranger_angles = np.arctan2(self.rangers[:,1],self.rangers[:,0])
        self.r_beam = np.radians(60)/2
        self.r_dist = 500
        
        
        self.cfgdone = True
        
        self.startup()
        
        
    def startup(self):
        self.reset()
        self.car.Servo.angle = 10
        self.car.Servo.desiredangle = 10
        self.car.Drive.speed = 0
        self.car.Drive.desiredspeed = 100
        self.car.Drive.initd = True
        
    def reset(self):
        self.end = 0;
        self.car.reset()
        self.background.reset()
        self.walls = [Wall((randint(*self.wall_range),self.car.pos_x-self.wall_spacing))]
        self.wall_loc = 0
        self.speed_change(0)
        
    def speed_change(self,dir):
        if dir == 1:
            if self.car.Drive.maxspeed > 95:
                return
            self.car.Drive.maxspeed *= 1.1
            self.car.start_speed *= 1.1
            self.car.dead_speed *= 1.1
            self.car.Drive.maxchange *= 1.1
        elif dir == -1:
            if self.car.Drive.maxspeed < 10:
                return
            self.car.Drive.maxspeed /= 1.1
            self.car.start_speed /= 1.1
            self.car.dead_speed /= 1.1
            self.car.Drive.maxchange /= 1.1
        else:
            (self.car.Drive.maxspeed,self.car.Drive.maxchange,self.car.start_speed,self.car.dead_speed) = self.car_defaults
        print(self.car.Drive.maxspeed)
            
        
        ## Comment to not reset SlideSwitches, let state propogate
        #for SS in self.SS:
        #    SS.reset()  
    
    def update(self):
        # Update peripheral timing
        self.ctlmod.timestep(SIMSTEP)
        
        # Update mechanical components
        self.car.Servo.setdc(self.ctlmod.xbr.getpin(0,4,'CCM'),self.ctlmod.pca0.Tperiod)
        self.car.Drive.setdc(self.ctlmod.xbr.getpin(0,5,'CCM'),self.ctlmod.pca0.Tperiod)
        
        # Move the obstacle
        #if self.target_hit:
        #    self.target.rot_rect.center = pygame.mouse.get_pos()
            
            
        # Move the car
        self.car.update()
        #self.car.pos_y -= 2
        
        # Move the background
        diff = (self.car.pos_y - self.car.pos_y_orig)
        self.background.update(np.array([0,diff]))

        # Move the walls
        # Wall.move_all(self.car.center() - self.car.centerorig())
        for wall in self.walls:
            wall.move(diff)
        # mark where the car is within the walls
        if self.car.pos_y_orig <= self.walls[self.wall_loc].rect.centery:
            self.wall_loc += 1
        elif self.wall_loc:
            if self.car.pos_y_orig >= self.walls[self.wall_loc-1].rect.centery:
                self.wall_loc -= 1
        #make a new wall as needed
        if self.walls[-1].rect.centery-self.wall_spacing > -Wall._thick:
            self.walls.append(Wall((randint(*self.wall_range),self.walls[-1].rect.centery-self.wall_spacing)))
            
        
        # Move the car back to starting point
        self.car.pos_y -= diff
        
        #self.car.collidecirc(self.target.rot_rect.center,self.target.radius)
        #self.ctlmod.ranger.setecho(self.car.detectobstacle())
        
        # Emit the switch values
        for SS in self.SS:
            self.ctlmod.xbr.setpin(SS.port,SS.pin,SS.val)
        # Emit the PB value
        self.ctlmod.xbr.setpin(self.PB.port,self.PB.pin,self.PB.val)
            
        # report sensor values
        dists = self.calc_rangers()/self.scale
        
        self.ctlmod.ranger.setecho(echo1cm=dists[0],echo2cm=dists[1],echo3cm=dists[2])
        self.ctlmod.compass.setdirection(-self.car.angle)

        self.end = self.detect_collision()
        if self.end:
            print(self.end)
        
        
        
    def detect_collision(self):
        # Step 1: Check if collide with bottom wall:
        if self.car.rect.colliderect(self.lwall):
            return 1
        elif self.car.rect.colliderect(self.rwall):
            return 2
        elif self.car.rect.colliderect(self.walls[self.wall_loc].rect):
            if self.col_points[2][0] < 0 and self.col_points[3][0] > 0:
                return self.car_edge_collide(self.col_points[2:])
            else:
                return 3
        elif not self.wall_loc:
            return 0
        elif self.car.rect.colliderect(self.walls[self.wall_loc-1]):
            if self.col_points[0][0] < 0 and self.col_points[1][0] > 0:
                return self.car_edge_collide(self.col_points[0:2])
            else:
                return 4
        else:
            return 0
    
    def car_edge_collide(self,pnts):
        anglesin = np.sin(self.car.angle)
        anglecos = np.cos(self.car.angle)
        txmatrix = np.array([[anglecos,anglesin],[-anglesin,anglecos]])
        for pnt in pnts:
            pnt = txmatrix.dot(pnt)
            #print(pnt)
            if self.car_base.collidepoint(pnt):
                return -1
        return 0
            
    def calc_rangers(self):
        angles = np.mod(self.ranger_angles + self.car.angle,2*np.pi)
        anglesin = np.sin(-self.car.angle)
        anglecos = np.cos(-self.car.angle)
        txmatrix = np.array([[anglecos,anglesin],[-anglesin,anglecos]])
        vects = [txmatrix.dot(x) for x in self.rangers]
        w1 = np.array([np.nan,np.nan])
        if self.wall_loc:
            #print('bottom wall {}'.format(self.wall_loc))
            w1 = (self.walls[self.wall_loc-1].rect.center - self.car.center())*[1,-1]
        w2 = (self.walls[self.wall_loc].rect.center - self.car.center())*[1,-1]

        points = np.array([w1 - [Wall.opening,0],
                           w1 + [Wall.opening,0],
                           w2 - [Wall.opening,0],
                           w2 + [Wall.opening,0]])
        self.col_points = points.copy()
        # calculate for each ranger
        p_dists = []
        wb_dists = []
        wt_dists = []
        wl_dists = []
        wr_dists = []
        dists = []
        ranger_num = 0
        for ranger,angle in zip(vects,angles):
            ranger_num+=1
            # Calculate distance to points
            p_vects = points - ranger
            p_angles = np.arctan2(p_vects[:,1],p_vects[:,0])-angle
            p_angles = np.mod(p_angles,2*np.pi)
            p_angles -= 2*np.pi*(p_angles > np.pi)
            in_view = 1*(p_angles >= -self.r_beam)*(p_angles <= self.r_beam)
            if np.any(in_view):
                p_dist = np.linalg.norm(p_vects[np.where(in_view)],axis=1)
                p_dists.append(np.amin(p_dist))
            else:
                p_dists.append(np.nan)
            #calculate distance to walls
            beam_edges = np.mod(angle + np.array([-self.r_beam,self.r_beam]),2*np.pi)
            
            
            #if ranger_num != 1:
            #    continue
            # Bottom wall
            # First, check if in between opening and can see the wall
            if True:
                wall_done = False
                if points[0][0] <= ranger[0] <= points[1][0]:
                    # Two cases here: Edge(s) detected, or no edges detected. We only care if edges are detected here
                    if in_view[0] or in_view[1]:
                        wb_dists.append(np.nan)
                        wall_done = True
                if not wall_done:
                    # If neither of the above, check if pointing straight through
                    #print(np.mod(p_angles,2*np.pi))
                    if (p_angles[0] < -self.r_beam) and (p_angles[1] > self.r_beam):
                        wb_dists.append(500)
                    # If both edges in view
                    elif in_view[0] and in_view[1]:
                        wb_dists.append(self.calc_horiz_wall_dist(ranger,beam_edges,points[0][1]))
                    # If one edge in view
                    elif in_view[0]:
                        if ranger[0] > points[1][0]:
                            wb_dists.append(np.nan)
                        else:
                            wb_dists.append(self.calc_horiz_wall_dist(ranger,beam_edges,points[0][1]))
                    elif in_view[1]:
                        if ranger[1] < points[0][0]:
                            wb_dists.append(np.nan)
                        else:
                            wb_dists.append(self.calc_horiz_wall_dist(ranger,beam_edges,points[0][1]))
                    # No edges in view
                    else:
                        #pointing away from wall
                        if (beam_edges[0] <= np.pi) and (beam_edges[1] <= np.pi):
                            wb_dists.append(np.nan)
                        else:
                            wb_dists.append(self.calc_horiz_wall_dist(ranger,beam_edges,points[0][1]))
                #print(wb_dists)
                
            # Repeat for Top Wall
            # First, check if in between opening and can see the wall
            if True:
                wall_done = False
                if points[2][0] <= ranger[0] <= points[3][0]:
                    # Two cases here: Edge(s) detected, or no edges detected. We only care if edges are detected here
                    if in_view[2] or in_view[3]:
                        #print("Centered, point detected")
                        wt_dists.append(np.nan)
                        wall_done = True
                if not wall_done:
                    # If neither of the above, check if pointing straight through
                    #print(np.mod(p_angles,2*np.pi))
                    if (p_angles[2] > self.r_beam) and (p_angles[3] < -self.r_beam):
                        #print("Straight Through")
                        wt_dists.append(np.nan)
                    # If both edges in view
                    elif in_view[2] and in_view[3]:
                        #print("Both Edges, outside")
                        wt_dists.append(self.calc_horiz_wall_dist(ranger,beam_edges,points[2][1]))
                    # If one edge in view
                    elif in_view[2]:
                        #print("Left Edge, outside")
                        if ranger[0] > points[3][0]:
                            wt_dists.append(np.nan)
                        else:
                            wt_dists.append(self.calc_horiz_wall_dist(ranger,beam_edges,points[2][1]))
                    elif in_view[3]:
                        #print("Right Edge, outside")
                        if ranger[1] < points[2][0]:
                            wt_dists.append(np.nan)
                        else:
                            wt_dists.append(self.calc_horiz_wall_dist(ranger,beam_edges,points[2][1]))
                    # No edges in view
                    else:
                        #pointing away from wall
                        if (beam_edges[0] >= np.pi) and (beam_edges[1] >= np.pi):
                            #print("No edges, pointing away")
                            wt_dists.append(np.nan)
                        else:
                            #print("No edges, pointing towards")
                            wt_dists.append(self.calc_horiz_wall_dist(ranger,beam_edges,points[2][1]))
            
            # Detect left wall
            if True:
                wl_dists.append(self.calc_vert_wall_dist(ranger[0]+self.car.pos_x,beam_edges,0))
                #print(wl_dists)
            
            # Detect right wall
            if True:
                wr_dists.append(self.calc_vert_wall_dist(ranger[0]+self.car.pos_x,beam_edges,self.size[0]))
                #print(wr_dists)
        dists = np.array([np.array(p_dists),
                          np.array(wb_dists),
                          np.array(wt_dists),
                          np.array(wl_dists),
                          np.array(wr_dists)])
        #print(dists)
        return np.nanmin(dists,0)
        #print(dists)
        
    def calc_vert_wall_dist(self,origin,beam_edges,wall_x):
        edges = beam_edges.copy()
        wall_x -= origin
        if wall_x < 0:
            edges = np.pi-beam_edges
            edges = np.flip(edges)
            wall_x *= -1
        edges -=2*np.pi*(edges>np.pi)
        if edges[0] <= 0 and edges[1] >= 0:
            return wall_x
        elif edges[0] >= np.pi/2 or edges[1] <= -np.pi/2:
            return np.nan
        elif edges[0] > 0:
            return wall_x/np.cos(edges[0])
        else:
            return wall_x/np.cos(edges[1])
            
    def calc_horiz_wall_dist(self,origin,beam_edges,wall_y):
        edges = beam_edges.copy()
        wall_y -= origin[1]
        if wall_y < 0:
            #print("here")
            edges = 2*np.pi-beam_edges
            edges = np.flip(edges)
            wall_y *= -1
        #print(edges)
        edges -=2*np.pi*(edges>np.pi)
        if edges[0] < np.pi/2 and edges[1] > np.pi/2:
            #print("perp")
            return wall_y
        elif edges[0] > np.pi/2:
            #print("ledge")
            return wall_y/np.sin(edges[0])
        else:
            #print("redge")
            return wall_y/np.sin(edges[1])
    
    def anglediff(self,angle1,angle2):
        dangle = np.mod((angle1-angle2),2*np.pi)
        if dangle > np.pi:
            return dangle - 2*np.pi
        else:
            return dangle
            
    def checkdone(self):
        #if self.car.collidecirc(self.target.rot_rect.center,self.target.radius):
        #    self.end = 1
        #if not self.car.rect.colliderect(self.background.get_rect()):
        #    self.end = -1
        return bool(self.end)
            
    def setconfig(self,cfg):
        # Not config for this one
        self.cfgdone = True
        
    
    def blit(self):
        self.background.blit(self.screen)
        
        self.car.draw(self.screen)
        
        #if self.cfgdone:
            #pygame.draw.rect(self.screen,(255,255,255),self.startrect,width=3)
            #pygame.draw.rect(self.screen,(255,255,255),self.endrect,width=3)
            #self.screen.blit(self.endtext,self.rect_endtext)
        
        for SS in self.SS:
            SS.draw(self.screen)
        self.PB.draw(self.screen)
            
        self.screen.blit(self.info,self.info_rect)
        
        for wall in self.walls:
            wall.blit(self.screen)
            
        
        
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
                        
                self.update()
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
                    #endtext = font.render('COURSE COMPLETE',True,(0,200,0))
                    endtext = font.render('CRASH!',True,(255,0,0))
                    pygame.draw.rect(self.screen,(0,0,0),endrect,width=5)
                    pygame.draw.rect(self.screen,(255,255,255),endrect)
                    self.screen.blit(endtext,endtext.get_rect(center=endrect.center))
                elif self.end == -1:
                    endrect = pygame.Rect((0,0),(300,100))
                    endrect.center = scaleCoord(self.size/2,self.scale)
                    #endtext = font.render('COURSE COMPLETE',True,(0,200,0))
                    endtext = font.render('CRASH!',True,(255,0,0))
                    pygame.draw.rect(self.screen,(0,0,0),endrect,width=5)
                    pygame.draw.rect(self.screen,(255,255,255),endrect)
                    self.screen.blit(endtext,endtext.get_rect(center=endrect.center))
                elif self.end == -2:
                    endrect = pygame.Rect((0,0),(400,100))
                    endrect.center = scaleCoord(self.size/2,self.scale)
                    #endtext = font.render('COURSE COMPLETE',True,(0,200,0))
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
        
        
        
