# This is just a selection dialog for what lab to run
# Could have easily been done with Tkinter, but didn't
# Want to have to package another module 

import pygame
import sys,os

SIZEX = 200
SIZEY = 300

def labselect(ctlmod,runctl,asset_path=None,force_lab=None):
    pygame.init()
    pygame.font.init()
    clock = pygame.time.Clock()
    screen = pygame.display.set_mode((SIZEX,SIZEY))
    pygame.display.set_caption("Select a Laboratory...")
    
    background = pygame.Surface(screen.get_size()).convert()
    background.fill((225,225,225))
    
    # Get file locations
    if asset_path is None:
        try:
            base_path = sys._MEIPASS #@UndefinedVariable
        except Exception:
            base_path = os.path.abspath(".")
        asset_path = base_path+"/assets/"
        lab_path = base_path+"/labs/"
    
    pygame.display.set_icon(pygame.image.load(asset_path+"icon.png"))
    
    lab_names = ['Lab 1-1','Lab 1-2','Lab 2','Lab 3','Lab 4','Lab 5','Lab 6']
    sim_files = ['lab11game','lab12game','lab2game','lab3game','lab4game','lab5game','lab6game']
    
    centerx = SIZEX/2
    sepy = int(SIZEY-4)/len(lab_names)
    font = pygame.font.SysFont('Sans',20)
    texts = []
    avail = []
    for i,text in enumerate(lab_names):
        if os.path.exists(lab_path+sim_files[i]+".py"):
            avail.append(True)
            texts.append(font.render(text,True,(0,0,0)))
        else:
            avail.append(False)
            texts.append(font.render(text,True,(127,127,127)))
            
    
    
    bgrectw = int(SIZEX-10)
    bgrecth = int(sepy-5)
    
    
    text_rects = []
    bg_rects = []
    currsep = sepy/2+2
    for i,text in enumerate(texts):
        text_rects.append(text.get_rect())
        text_rects[-1].center = (centerx,currsep)
        bg_rects.append(text_rects[-1].copy())
        bg_rects[-1].width = bgrectw
        bg_rects[-1].height = bgrecth
        bg_rects[-1].center = text_rects[-1].center
        
        currsep += sepy 
        
    
    selected = False
    downrect = -1
    if force_lab:
        selected = True
        if force_lab == 11:
            downrect = 0
        elif force_lab == 12:
            downrect = 1
        else:
            downrect  = force_lab
    while not selected and runctl:
        for event in pygame.event.get():
            pass
            if event.type == pygame.QUIT:
                    pygame.quit()
                    return
            elif event.type == pygame.MOUSEBUTTONDOWN:
                for i,bg_rect in enumerate(bg_rects):
                    if bg_rect.collidepoint(pygame.mouse.get_pos()) and avail[i]:
                        downrect = i
            elif event.type == pygame.MOUSEBUTTONUP:
                if downrect != -1:
                    if bg_rects[downrect].collidepoint(pygame.mouse.get_pos()):
                        selected = True
                    else:
                        downrect = -1
        screen.blit(background,(0,0))     
        for i,text in enumerate(texts):
            if i == downrect:
                pygame.draw.rect(background,(255,255,255),bg_rects[i])
            else:
                pygame.draw.rect(background,(165,165,165),bg_rects[i])
            screen.blit(text,text_rects[i])
        pygame.display.flip()
        clock.tick(60)
        
    pygame.quit()
    print("Selected Lab ? {}".format(downrect))
    
    sys.path.append(lab_path)
    if downrect == 0:
        from lab11game import Simulation # @UnresolvedImport # @UnusedImport # @Reimport
    if downrect == 1:
        from lab12game import Simulation # @UnresolvedImport # @UnusedImport # Reimport
    elif downrect == 2:
        from lab2game import Simulation # @UnresolvedImport # @UnusedImport # @Reimport
    elif downrect == 3:
        from lab3game import Simulation # @UnresolvedImport # @UnusedImport # @Reimport
    elif downrect == 4:
        from lab4game import Simulation # @UnresolvedImport # @UnusedImport # @Reimport
    elif downrect == 5:
        from lab5game import Simulation # @UnresolvedImport # @UnusedImport # @Reimport
    elif downrect == 6:
        from lab6game import Simulation # @UnresolvedImport # @UnusedImport # @Reimport
    sim = Simulation(ctlmod,runctl,asset_path)
    sim.run()
        
if __name__ == "__main__":
    labselect(0,1)
                        
                
        
        
        
        
        
        
        