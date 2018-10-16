import sc2
from sc2 import run_game, maps, Race, Difficulty, position, Result
from sc2.player import Bot, Computer
from sc2.constants import NEXUS, PROBE, PYLON, ASSIMILATOR, GATEWAY, CYBERNETICSCORE, STALKER, STARGATE, VOIDRAY, OBSERVER, ROBOTICSFACILITY
import random
import cv2
import numpy as np
import time
import keras


HEADLESS = True

class Apollyon(sc2.BotAI):
	def __init__(self, use_model=False):
		# self.ITERATIONS_PER_MINUTE = 170
		self.MAX_WORKERS = 40
		self.do_something_after = 0
		self.train_data = []
		self.scout_and_spots = {}



	def on_end(self, game_result):
		print('---end_game---')
		print(game_result)	


		if game_result == Result.Victory:
			np.save("train_data/{}.npy".format(str(int(time.time()))), np.array(self.train_data))

	async def on_step(self, time):
		# self.iteration = iteration
		self.time = (self.state.game_loop/22.4) / 60
		await self.scout()
		await self.distribute_workers()
		await self.build_workers()
		await self.build_pylons()
		await self.build_assimilators()
		await self.expand()
		await self.build_barracks()
		await self.build_army()
		await self.intel()
		await self.attack()

###################################################################### OPENCV VIZUALIZATION #################################################################################


	def random_location_variance(self, enemy_start_location):
		x = enemy_start_location[0]
		y = enemy_start_location[1]

		x += ((random.randrange(-20, 20))/100) * enemy_start_location[0]
		y += ((random.randrange(-20, 20))/100) * enemy_start_location[1]

		if x < 0:
			x = 0
		if y < 0:
			y = 0
		if x > self.game_info.map_size[0]:
			x = self.game_info.map_size[0]
		if y > self.game_info.map_size[1]:
			y = self.game_info.map_size[1]

		go_to = position.Point2(position.Pointlike((x,y)))    ## Coordinates with elevation level included
		return go_to
		
	async def scout(self):
		# {DISTANCE_TO_ENEMY_START:EXPANSIONLOC}
		self.expand_dis_dir = {}


	async def intel(self):
		game_data = np.zeros((self.game_info.map_size[1], self.game_info.map_size[0], 3), np.uint8)  ## width by hight - reversed for array, colors, datatype

		draw_dict = {
					 NEXUS: [15, (0, 255, 0)],
					 PYLON: [3, (20, 235, 0)],
					 PROBE: [1, (55, 200, 0)],

					 ASSIMILATOR: [2, (55, 200, 0)],
					 GATEWAY: [3, (200, 100, 0)],
					 CYBERNETICSCORE: [3, (150, 150, 0)],
					 STARGATE: [5, (255, 0, 0)],
					 VOIDRAY: [3, (255, 100, 0)],
					}



		for unit_type in draw_dict:
			for unit in self.units(unit_type).ready:
				pos = unit.position
				cv2.circle(game_data, (int(pos[0]), int(pos[1])), draw_dict[unit_type][0], draw_dict[unit_type][1], -1)  ## draw objects on a cv map

		## DRAW ENEMY BASE/UNITS		

		main_base_names = ["nexus", "commandcenter", "hatchery"]
		for enemy_building in self.known_enemy_structures:
			pos = enemy_building.position
			if enemy_building.name.lower() not in main_base_names:
				cv2.circle(game_data, (int(pos[0]), int(pos[1])), 5, (200, 50, 212), -1)
		for enemy_building in self.known_enemy_structures:
			pos = enemy_building.position
			if enemy_building.name.lower() in main_base_names:
				cv2.circle(game_data, (int(pos[0]), int(pos[1])), 15, (0, 0, 255), -1)		

		for enemy_unit in self.known_enemy_units:

			if not enemy_unit.is_structure:
				worker_names = ["probe",
								"scv",
								"drone"]
				pos = enemy_unit.position
				if enemy_unit.name.lower() in worker_names:
					cv2.circle(game_data, (int(pos[0]), int(pos[1])), 1, (55, 0, 155), -1)
				else:
					cv2.circle(game_data, (int(pos[0]), int(pos[1])), 3, (50, 0, 215), -1)

		for obs in self.units(OBSERVER).ready:
			pos = obs.position
			cv2.circle(game_data, (int(pos[0]), int(pos[1])), 1, (255, 255, 255), -1)        


		line_max = 50
		mineral_ratio = self.minerals / 1500
		if mineral_ratio > 1.0:
			mineral_ratio = 1.0


		vespene_ratio = self.vespene / 1500
		if vespene_ratio > 1.0:
			vespene_ratio = 1.0

		population_ratio = self.supply_left / self.supply_cap
		if population_ratio > 1.0:
			population_ratio = 1.0

		plausible_supply = self.supply_cap / 200.0

		military_weight = len(self.units(VOIDRAY)) / (self.supply_cap-self.supply_left)
		if military_weight > 1.0:
			military_weight = 1.0


		cv2.line(game_data, (0, 19), (int(line_max*military_weight), 19), (250, 250, 200), 3)  # worker/supply ratio
		cv2.line(game_data, (0, 15), (int(line_max*plausible_supply), 15), (220, 200, 200), 3)  # plausible supply (supply/200.0)
		cv2.line(game_data, (0, 11), (int(line_max*population_ratio), 11), (150, 150, 150), 3)  # population ratio (supply_left/supply)
		cv2.line(game_data, (0, 7), (int(line_max*vespene_ratio), 7), (210, 200, 0), 3)  # gas / 1500
		cv2.line(game_data, (0, 3), (int(line_max*mineral_ratio), 3), (0, 255, 25), 3)  # minerals minerals/1500
					


		## VIZUALIZATION FLIP

		self.flipped = cv2.flip(game_data, 0)  ## flip the image

		if not HEADLESS:
			resized = cv2.resize(self.flipped, dsize=None, fx=2, fy=2)	## enlarge 2x 
			cv2.imshow('Intel', resized)
			cv2.waitKey(1)


####################################################################### GAME METHODS ##########################################################################

	async def build_workers(self):
		if len(self.units(NEXUS))*16 > len(self.units(PROBE)):   ## restrict workers to 16 per Nexus
			if len(self.units(PROBE)) < self.MAX_WORKERS:
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
		if self.units(NEXUS).amount < self.time/2 and self.can_afford(NEXUS):     ## add new bases
			await self.expand_now()

	async def build_barracks(self):
		if self.units(PYLON).ready.exists:				## if there is a pylon										
			pylon = self.units(PYLON).ready.random		## pick random pylon

			if self.units(GATEWAY).ready.exists and not self.units(CYBERNETICSCORE):		## if gateway already exists and there is no cybercore
					if self.can_afford(CYBERNETICSCORE) and not self.already_pending(CYBERNETICSCORE):	
						await self.build(CYBERNETICSCORE, near=pylon)		## build cybercore

			elif len(self.units(GATEWAY)) < 1:   ## Amount of Gateways grows with every minute
				if self.can_afford(GATEWAY) and not self.already_pending(GATEWAY):
					await self.build(GATEWAY, near=pylon)

			if self.units(CYBERNETICSCORE).ready.exists:
				if len(self.units(ROBOTICSFACILITY)) < 1:
					if self.can_afford(ROBOTICSFACILITY) and not self.already_pending(ROBOTICSFACILITY):
						await self.build(ROBOTICSFACILITY, near=pylon)					

			if self.units(CYBERNETICSCORE).ready.exists:		## if gateway already exists and there is no cybercore
				if len(self.units(STARGATE)) < self.time/2:
					if self.can_afford(STARGATE) and not self.already_pending(STARGATE):	
						await self.build(STARGATE, near=pylon)		## build cybercore



	async def build_army(self):
		for gateway in self.units(GATEWAY).ready.noqueue:	
			if not self.units(STALKER).amount > self.units(VOIDRAY).amount:		
				if self.can_afford(STALKER) and self.supply_left > 0:		## Stalkers
					await self.do(gateway.train(STALKER))

		for stargate in self.units(STARGATE).ready.noqueue:			
			if self.can_afford(VOIDRAY) and self.supply_left > 0:		## Void Rays
				await self.do(stargate.train(VOIDRAY))		


	def find_target(self, state):	
		if len(self.known_enemy_units) > 0:						## if there are any knwon units
			return random.choice(self.known_enemy_units)		## return random one as a target
		elif len(self.known_enemy_structures) > 0:				## ...or there any known structures
			return random.choice(self.known_enemy_structures)
		else:
			return self.enemy_start_locations[0]				## ... otherwise go to enemy start location		

	async def attack(self):

		if len(self.units(VOIDRAY).idle) > 0:

			target = False
			if self.time > self.do_something_after:
				if self.use_model:
					prediction = self.model.predict([self.flipped.reshape([-1, 176, 200, 3])])
					choice = np.argmax(prediction[0])
					#print('prediction: ',choice)

					choice_dict = {0: "No Attack!",
								   1: "Attack close to our nexus!",
								   2: "Attack Enemy Structure!",
								   3: "Attack Eneemy Start!"}

					print("Choice #{}:{}".format(choice, choice_dict[choice]))

				else:
					choice = random.randrange(0, 4)


			## learn to not attack when low on units
	 
				if choice == 0:
					# no attack
					wait = random.randrange(7, 100) / 100
					self.do_something_after = self.time + wait

			## learn to attack close enemy			

				elif choice == 1:								
					#attack_unit_closest_nexus
					if len(self.known_enemy_units) > 0:
						target = self.known_enemy_units.closest_to(random.choice(self.units(NEXUS)))

			## learn to attack enemy structures			

				elif choice == 2:
					
					if len(self.known_enemy_structures) > 0:		
						target = random.choice(self.known_enemy_structures)

			## learn to attack enemy tart location 				

				elif choice == 3:							
					#attack_enemy_start
					target = self.enemy_start_locations[0]


				if target:
					for vr in self.units(VOIDRAY).idle:
						await self.do(vr.attack(target))

				## produce [1,0,0,0] output			
						
				y = np.zeros(4)
				y[choice] = 1
				print(y)
				self.train_data.append([y,self.flipped])				

				




run_game(maps.get("AbyssalReefLE"),[
	Bot(Race.Protoss, Apollyon(use_model=True)),
	Computer(Race.Terran, Difficulty.Easy)],
	realtime=False)		