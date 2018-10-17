import sc2
from sc2 import run_game, maps, Race, Difficulty
from sc2.player import Bot, Computer
from sc2.constants import *
import random



class Apollyon(sc2.BotAI):
    async def on_step(self, iteration):
        await self.distribute_workers()
        await self.build_scv()
        await self.build_supplydepot()
        await self.idle_scv()
        await self.expand()
        await self.build_refinery()
        await self.build_barracks()
        await self.build_factory()
        await self.build_marine()


    async def idle_scv(self):        
        centers = self.units(COMMANDCENTER).first
        for scv in self.units(SCV).idle:
            await self.do(scv.gather(self.state.mineral_field.closest_to(centers)))        


    async def build_scv(self):
        for center in self.units(COMMANDCENTER).ready.noqueue:
            if self.can_afford(SCV):
                await self.do(center.train(SCV))


    async def build_supplydepot(self):
        centers = self.units(COMMANDCENTER).first           
        if self.can_afford(SUPPLYDEPOT) and self.units(SUPPLYDEPOT).amount < 30:
            if not self.units(SUPPLYDEPOT).exists or (self.units(BARRACKS).amount / self.units(SUPPLYDEPOT).amount) >= 0.2:
                await self.build(SUPPLYDEPOT, near=centers.position.towards(self.game_info.map_center, 8))        


    async def expand(self):
        if self.units(COMMANDCENTER).amount < 2 and self.can_afford(COMMANDCENTER):
            await self.expand_now()      
            
    async def build_refinery(self):
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


    async def build_barracks(self):
        centers = self.units(COMMANDCENTER).first
        if self.units(SUPPLYDEPOT).exists:
            if self.can_afford(BARRACKS) and self.units(BARRACKS).amount < 5:
                await self.build(BARRACKS, near=centers.position.towards(self.game_info.map_center, 8))


    async def build_factory(self):
        centers = self.units(COMMANDCENTER).first
        if self.units(BARRACKS).exists:
            if self.units(FACTORY).amount < 1 and not self.already_pending(FACTORY):
                if self.can_afford(FACTORY):    
                    p = centers.position.towards_with_random_angle(self.game_info.map_center, 16)
                    await self.build(FACTORY, near=p)


    async def build_marine(self):
        for barrack in self.units(BARRACKS).ready.noqueue:
            if self.can_afford(MARINE) and self.supply_left > 0:
                await self.do(barrack.train(MARINE))


    async def build_cyclone(self):
                    

    async def build_starport(self)            
                    



                       




run_game(maps.get("AbyssalReefLE"), [
    Bot(Race.Terran, Apollyon()),
    Computer(Race.Protoss, Difficulty.Easy)
    ], realtime=False)      
