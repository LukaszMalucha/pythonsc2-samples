import sc2
from sc2 import run_game, maps, Race, Difficulty, position
from sc2.player import Bot, Computer
from sc2.constants import *
import random



class Apollyon(sc2.BotAI):
    def __init__(self):
        self.MAX_WORKERS = 54



    async def on_step(self, iteration):
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
        await self.attack()
      


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
        if self.units(COMMANDCENTER).amount < 4 and self.can_afford(COMMANDCENTER):
            await self.expand_now()     

            
    async def build_refinery(self):
        if self.units(SUPPLYDEPOT).exists:
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
            else:
               await self.do(lab(AbilityId.RESEARCH_STIMPACK))        


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


    async def attack(self):
        centers = self.units(COMMANDCENTER)[-1]
        army_units = {MARINE: [30, 10],           ## group units (attack/def)
                    MARAUDER: [15, 4],
                    MEDIVAC:  [3, 0]}

        for UNIT in army_units:                     ## Attack group
            if self.units(UNIT).amount > army_units[UNIT][0] and self.units(UNIT).amount > army_units[UNIT][1]:
                for s in self.units(UNIT).idle:               
                    await self.do(s.attack(self.find_target(self.state)))

            elif self.units(UNIT).amount > army_units[UNIT][1]:                 ## Defend & gather until enough to attack
                if len(self.known_enemy_units) > 0:
                    for s in self.units(UNIT).idle:
                        await self.do(s.attack(random.choice(self.known_enemy_units)))  

            elif self.units(UNIT).amount < army_units[UNIT][0]: 
                if len(self.known_enemy_units) < 0:
                    for s in self.units(UNIT).idle:
                        center = self.game_info.map_center
                        move_unit = position.Point2(position.Pointlike(center))
                        await self.do(s.move(move_unit))        



run_game(maps.get("AbyssalReefLE"), [
    Bot(Race.Terran, Apollyon()),
    Computer(Race.Protoss, Difficulty.Medium)
    ], realtime=False)      
