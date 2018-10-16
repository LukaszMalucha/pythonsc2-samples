import sc2
from sc2 import run_game, maps, Race, Difficulty
from sc2.player import Bot, Computer
from sc2.constants import NEXUS, PROBE, PYLON, ASSIMILATOR, GATEWAY, CYBERNATICSCORE, STALKER
import random


class Apollyon(sc2.BotAI):
	async def on_step(self, iteration):
		await self.distribute_workers()
		await self.build_workers()
		await self.build_pylons()
		await self.build_assimilators()
		await self.expand()
		await self.build_barracks()
		await self.build_army()
		await self.attack()

	async def build_workers(self):
		for nexus in self.units(NEXUS).ready.noqueue:	
			if self.can_afford(PROBE):					## train if there is enough minerals
				await self.do(nexus.train(PROBE))		## build


	async def build_pylons(self):
		if self.supply_left < 5	and not self.already_pending(PYLON):	## if less than 5 population
			nexuses = self.units(NEXUS).ready							## ...and nexus queue empty
			if nexuses.exists:											## ...and nexus exist
				if self.can_afford(PYLON):								## ...and enough minerals
					await self.build(PYLON, near=nexuses.first)			## ...build near the first nexus	

	async def build_assimilators(self):
		for nexus in self.units(NEXUS).ready:							
			vespenes = self.state.vespene_geyser.closer_than(10.0, nexus)	## closest vespene geysers
			for vespene in vespenes:
				if not self.can_afford(ASSIMILATOR):					## if not enough minerals
					break
				worker = self.select_build_worker(vespene.position)		## pick closest worker
				if worker is None:										## ... if there is none
					break
				if not self.units(ASSIMILATOR).closer_than(1.0, vespene).exists: ## if there is no assimilator actually
					await self.do(worker.build(ASSIMILATOR, vespene))	


	async def expand(self):
		if self.units(NEXUS).amount < 3 and self.can_afford(NEXUS):     ## add new bases
			await self.expand_now()

	async def build_barracks(self):
		if self.units(PYLON).ready.exists:				## if there is a pylon										
			pylon = self.units(PYLON).ready.random		## pick random pylon

			if self.units(GATEWAY).ready.exists and not self.units(CYBERNATICSCORE):		## if gateway already exists and there is no cybercore
					if self.can_afford(CYBERNATICSCORE) and not self.already_pending(CYBERNATICSCORE):	
						await self.build(CYBERNATICSCORE, near=pylon)		## build cybercore
						
			elif len(self.units(GATEWAY)) < 3:
				if self.can_afford(GATEWAY) and not self.already_pending(GATEWAY):
					await self.build(GATEWAY, near=pylon)

	async def build_army(self):
		for gateway in self.units(GATEWAY).ready.noqueue:			
			if self.can_afford(STALKER) and self.supply_left > 0:
				await self.do(gw.train(STALKER))

	def find_target(self, state):	
		if len(self.known_enemy_units) > 0:						## if there are any knwon units
			return random.choice(self.known_enemy_units)		## return random one as a target
		elif len(self.knwon_enemy_structures) > 0:				## ...or there any known structures
			return random.choice(self.known_enemy_structures)
		else:
			return self.enemy_start_locations[0]				## ... otherwise go to enemy start location		

	async def attack(self):										
		if self.units(STALKER).amount > 15:						## get 15 units	
			for s in self.units(STALKER).idle:
				await self.do(s.attack(self.find_target(self.state)))	## exercise find_target method



		if self.units(STALKER).amount > 3:										## defend base option
			if len(self.known_enemy_units) > 0
			for s in self.units(STALKER).idle:
				await self.do(s.attack(random.choice(self.known_enemy_units)))										

				




run_game(maps.get("AbyssalReefLE"),[
	Bot(Race.Protoss, Apollyon()),
	Computer(Race.Terran, Difficulty.Easy)],
	realtime=False)		