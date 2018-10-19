import sc2
from sc2 import run_game, maps, Race, Difficulty, position, Result
from sc2.player import Bot, Computer
from sc2.constants import *
import random
import cv2
import numpy as np
import time

HEADLESS = True

class Apollyon(sc2.BotAI):
    def __init__(self):
        self.ITERATIONS_PER_MINUTE = 170        
        self.MAX_WORKERS = 54
        self.choose_next_action = 0
        self.training_data = []

    def endgame(self, game_result):
        print('---end_game---')
        print(game_result)  


        # if game_result == Result.Victory:
        np.save("training_data/{}.npy".format(str(int(time.time()))), np.array(self.training_data))    



    async def on_step(self, iteration):
        self.iteration = iteration
        await self.distribute_workers()
        await self.build_scv()
        await self.build_supplydepot()
        await self.expand()
        await self.build_refinery()
        await self.build_barracks()
        await self.upgrade_barracks()
        await self.upgrade_combatshield()
        await self.build_factory()
        await self.build_starport()
        await self.build_army()
        await self.game_map()
        await self.defend()
        await self.attack()
      

###################################################################### OPENCV VIZUALIZATION #################################################################################

    async def game_map(self):

        ## INITIAL IMAGE - NP ARRAY
        game_data = np.zeros((self.game_info.map_size[1], self.game_info.map_size[0], 3), np.uint8)  ## width by hight - reversed for array!, colors, datatype

        ## COLOR CODING    
        objects = {
                     COMMANDCENTER: [15, (0, 255, 0)],
                     SUPPLYDEPOT: [3, (50, 220, 30)],                    
                     REFINERY: [2, (55, 220, 30)],
                     BARRACKS: [3, (133, 178, 128)],

                     SCV: [1, (240, 240, 240)],
                     MARINE: [2, (50, 100, 218)],
                     MARAUDER: [2, (10 , 20, 50)],
                     MEDIVAC: [3, (130, 150, 200)],
                    }


        ## DRAW OBJECTS                
        for unit_type in objects:
            for unit in self.units(unit_type).ready:  
                pos = unit.position
                cv2.circle(game_data, (int(pos[0]), int(pos[1])), objects[unit_type][0], objects[unit_type][1], -1)  ## draw objects on a cv map


        ## DRAW ENEMY BASE/UNITS        
        main_base_names = ["nexus", "commandcenter", "hatchery"]
        for enemy_building in self.known_enemy_structures:
            pos = enemy_building.position
            if enemy_building.name.lower() not in main_base_names:
                cv2.circle(game_data, (int(pos[0]), int(pos[1])), 3, (240, 30, 30), -1)    ## small circle for other buildings
        for enemy_building in self.known_enemy_structures:
            pos = enemy_building.position
            if enemy_building.name.lower() in main_base_names:
                cv2.circle(game_data, (int(pos[0]), int(pos[1])), 15, (255, 0, 0), -1)      ## bigger circle for hq    

        for enemy_unit in self.known_enemy_units:

            if not enemy_unit.is_structure:
                worker_names = ["probe",
                                "scv",
                                "drone"]
                pos = enemy_unit.position
                if enemy_unit.name.lower() in worker_names:
                    cv2.circle(game_data, (int(pos[0]), int(pos[1])), 1, (180, 70, 70), -1)
                else:
                    cv2.circle(game_data, (int(pos[0]), int(pos[1])), 2, (255, 0, 0), -1)
 


        ## VIZUALIZATION FLIP
        if not HEADLESS:
            self.flipped = cv2.flip(game_data, 0)  ## flip the image
            resized = cv2.resize(self.flipped, dsize=None, fx=2, fy=2)  ## enlarge 2x 
            cv2.imshow('game_map', resized)
            cv2.waitKey(1)


####################################################################### GAME METHODS ##########################################################################



    async def build_scv(self):
        for center in self.units(COMMANDCENTER).ready.noqueue:
            if len(self.units(SCV)) < self.MAX_WORKERS:  
                if (self.units(SCV).amount - self.units(MARINE).amount) < 48:        
                    if self.can_afford(SCV):
                        await self.do(center.train(SCV))


    async def build_supplydepot(self):
        centers = self.units(COMMANDCENTER).first           
        if self.supply_left < 10 and not self.already_pending(SUPPLYDEPOT):
            await self.build(SUPPLYDEPOT, near=centers.position.towards(self.game_info.map_center, 8))          


    async def expand(self):
        if self.units(COMMANDCENTER).amount < 3 and self.can_afford(COMMANDCENTER):
            await self.expand_now()     

            
    async def build_refinery(self):
        if self.units(SUPPLYDEPOT).exists:
            if self.vespene < 300:
                for center in self.units(COMMANDCENTER).ready:            
                        vespenes = self.state.vespene_geyser.closer_than(20.0, center)
                        for vespene in vespenes:
                            if not self.can_afford(REFINERY):
                                break
                            worker = self.select_build_worker(vespene.position)
                            if worker is None:
                                break
                            if not self.units(REFINERY).closer_than(1.0, vespene).exists:
                                await self.do(worker.build(REFINERY, vespene))                  




## MILITARY BUILDINGS

    async def build_barracks(self):
        centers = self.units(COMMANDCENTER).first
        if self.units(SUPPLYDEPOT).exists and self.units(COMMANDCENTER).amount == 3:
                if self.can_afford(BARRACKS) and self.units(BARRACKS).amount < 4:
                    if (self.units(BARRACKS).amount - self.units(MARINE).amount) < 1:
                        p = centers.position.towards_with_random_angle(self.game_info.map_center, 10)
                        await self.build(BARRACKS, near=p)


    async def upgrade_barracks(self):
        for barracks in self.units(BARRACKS).ready:
            if barracks.add_on_tag == 0:
                await self.do(barracks.build(BARRACKSTECHLAB))





    async def upgrade_combatshield(self):
        if self.units(BARRACKSTECHLAB).ready.exists:
          for lab in self.units(BARRACKSTECHLAB).ready:
            abilities = await self.get_available_abilities(lab)
            if AbilityId.RESEARCH_COMBATSHIELD in abilities and self.can_afford(AbilityId.RESEARCH_COMBATSHIELD):
               await self.do(lab(AbilityId.RESEARCH_COMBATSHIELD))        


    async def build_factory(self):
        centers = self.units(COMMANDCENTER).first
        if self.units(BARRACKS).exists:
            if self.units(FACTORY).amount < 1 and not self.already_pending(FACTORY):
                if self.units(MARINE).amount > 5:
                    if self.can_afford(FACTORY):    
                        await self.build(FACTORY, near=centers.position.towards(self.game_info.map_center, 14))


    async def build_starport(self):
        centers = self.units(COMMANDCENTER).first 
        if self.units(FACTORY).exists:
            if self.units(STARPORT).amount < 1 and not self.already_pending(STARPORT):
                if self.units(MARINE).amount > 5:
                    if self.can_afford(STARPORT):    
                        await self.build(STARPORT, near=centers.position.towards(self.game_info.map_center, 14)) 
       

## MILITARY UNITS  

## COMPOSITION ~ 8 Marines, 4 Marauders, 1 Medivac     
                    

    async def build_army(self):
        for barrack in self.units(BARRACKS).ready.noqueue:
            if self.can_afford(MARINE) and self.supply_left > 0:
                if self.units(MARINE).amount < 30:
                    await self.do(barrack.train(MARINE))


        for barrack in self.units(BARRACKS).ready.noqueue:
            if self.can_afford(MARAUDER) and self.supply_left > 0:
                await self.do(barrack.train(MARAUDER))


        for starport in self.units(STARPORT).ready.noqueue:
            if self.can_afford(MEDIVAC) and self.supply_left > 0:
                if self.units(MEDIVAC).amount < 5:
                    await self.do(starport.train(MEDIVAC))    





## ACTIONS

    def find_target(self, state):   
        if len(self.known_enemy_units) > 0:                     ## if there are any known units
            return random.choice(self.known_enemy_units)        ## return random one as a target
        elif len(self.known_enemy_structures) > 0:              ## ...or there any known structures
            return random.choice(self.known_enemy_structures)
        else:
            return self.enemy_start_locations[0]                ## ... otherwise go to enemy start location 



    async def defend(self):
        army = {MARINE: [24, 10],           ## group units (attack/def)
                MARAUDER: [12, 4],
                MEDIVAC:  [3, 0]}

        for UNIT in army:                     
            if self.units(UNIT).amount > army[UNIT][1]:                 ## Defend & gather until enough to attack
                if len(self.known_enemy_units) > 0:
                    for s in self.units(UNIT).idle:
                        await self.do(s.attack(random.choice(self.known_enemy_units)))  
    

    async def attack(self):

        army = {MARINE: [30, 10],           ## group units (attack/def)
                MARAUDER: [12, 5],
                MEDIVAC:  [3, 0]}

        for UNIT in army:           
            if self.units(UNIT).amount > army[UNIT][0]:
                choice = random.randrange(0, 4)
                target = False

                if self.iteration > self.choose_next_action:
                    if choice == 0:
                        # no attack
                        wait = random.randrange(20, 150)
                        self.choose_next_action = self.iteration + wait

                    elif choice == 1:
                        #attack_unit_closest_nexus
                        if len(self.known_enemy_units) > 0:
                            target = self.known_enemy_units.closest_to(random.choice(self.units(COMMANDCENTER)))

                    elif choice == 2:
                        #attack enemy structures
                        if len(self.known_enemy_structures) > 0:
                            target = random.choice(self.known_enemy_structures)

                    elif choice == 3:
                        #attack_enemy_start
                        target = self.enemy_start_locations[0]

                    if target:
                        for vr in self.units(UNIT).idle:
                            await self.do(vr.attack(target))

                    ## SAVE A CHOICE AS AN ARRAY [*,*,*,*]        
                    y = np.zeros(4)
                    y[choice] = 1
                    print(y)
                    self.training_data.append([y,self.flipped])



run_game(maps.get("AbyssalReefLE"), [
    Bot(Race.Terran, Apollyon()),
    Computer(Race.Protoss, Difficulty.Easy)
    ], realtime=False)      
