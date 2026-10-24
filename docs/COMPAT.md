# Compatibilité des jeux

Archipelago **0.6.7** (sources), Universal Tracker **Tracker_v0.3.0**, sur Raspberry Pi 5 (aarch64, Python 3.13).

Colonnes :
- **se charge** : le monde s'enregistre sous son nom de jeu (`scripts/check_apworlds.py`).
- **génère** : génération solo headless depuis le template d'options par défaut (`scripts/testenv/solo_check.py`).
- **niveau 1** : suivi générique validé contre un serveur local (`tests/test_level1_all22.py` : seed à 22 slots,
  noms résolus via le datapackage, compteurs identiques à ceux d'un vrai client).
- **UT sans yaml** : le monde déclare `ut_can_gen_without_yaml` (régénération à partir du `slot_data` seul).
- **UT avec yaml** : la logique est juste en régénérant le monde depuis le yaml du joueur (+ `slot_data`).
- **validé** : (1) comparaison de référence à chaque sphère avec le multiworld complet de génération, sur N seeds
  aux options tirées au hasard (`scripts/testenv/validate_logic.py`, outil dans un process séparé, `slot_data`
  passé comme par le réseau) ; (2) bout en bout : le bot ne coche que ce que l'API annonce en logique jusqu'au but
  de tous les slots (`tests/test_logic_e2e.py`). « logique » = `logic: true` dans `config/apworlds.yaml`.

Légende : ✅ oui · ❌ non · ⚠️ partiel · ⏳ pas encore testé · — sans objet

| Jeu | Version apworld | Se charge sur 0.6.7 | Génère en headless | Niveau 1 OK | UT sans yaml | UT avec yaml | Validé par test | Notes |
|---|---|---|---|---|---|---|---|---|
| Celeste (Open World) | core 0.6.7 | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ 10/10 seeds + e2e | Yaml nécessaire. Logique activée. Les options de logique (roomsanity, zone du but, fraises requises…) viennent du slot_data : un yaml d'une autre room marche aussi (validé 9/9, adaptateur `_celeste`) ; seule `goal_area_checkpointsanity` vient encore du yaml |
| Kingdom Hearts 2 | core 0.6.7 | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ 5/5 + e2e | Yaml nécessaire. Logique activée |
| Jak and Daxter: The Precursor Legacy | core 0.6.7 | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ 5/5 + e2e | Yaml nécessaire. Logique activée |
| The Wind Waker HD | Teotia444/twwhd-apworld `main` @ c2188264 (version de la room) | ✅ | ✅ | ✅ | ❌ | ✅ (adaptateur) | ✅ 7/7 + e2e (v1.0.2) ; 4/4 yaml de Romain + 4/4 aléatoires (`main`) | Adaptateur : entrées depuis `slot_data`, donjons requis déduits des locations. Releases « beta » uniquement, pas de manifeste ; la room a été générée avec `main` (Auction 100 Rupee, Dampa Pig Minigame). Distinct de « The Wind Waker » (core) |
| Super Mario 64 (sm64ex) | core 0.6.7 | ✅ | ✅ | ✅ | ❌ | ✅ (adaptateur) | ✅ 6/6 + e2e | Adaptateur : `AreaRando` du `slot_data`. Logique activée |
| Super Mario Odyssey | mdietz94/smo_archipelago v1.5.3 | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ 5/5 comparables + e2e | Nom de jeu **« Spicy Meatball Overdrive »**. Sa génération n'est pas reproductible d'un process à l'autre (ordre de remplissage) : certains runs de validation sont « non comparables », sans effet sur la logique. Logique activée |
| Ori and the Blind Forest | c-ostic/Archipelago v0.4.2 | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ 8/8 + e2e | Logique activée |
| Ori and the Will of the Wisps | Satisha10/APwotw_release v0.6.5 | ✅ | ✅ | ✅ | ✅ (incomplet) | ✅ yaml + slot_data | ✅ 5/5 yaml de Romain + e2e ; ⚠️ 3/4 aléatoires | Le `slot_data` ne couvre pas toutes les options : régénération depuis le yaml + `slot_data`. Adaptateurs : bug du spawn (coût des portes à keystones faux, aussi dans UT) et « Spawn item » en double. Avec certaines options aléatoires, quelques locations atteignables ne sont pas montrées (sous-estimation, jamais de location hors logique). Logique activée |
| Balatro | BurndiL/BalatroAP v0.1.9f | ✅ | ✅ | ✅ | ❌ | ✅ (adaptateur) | ✅ 5/5 aléatoires + 5/5 yaml de Romain + e2e | Adaptateur : decks, mises et lots de jokers rejoués depuis `slot_data`. Yaml nécessaire. Logique activée |
| Slay the Spire | cjmang/StS-AP-World 2.3.5 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ + e2e | Logique activée |
| Kingdom Hearts: Birth by Sleep Final Mix | gaithernOrg/ArchipelagoKHBBS 0.2.0 | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ 8/8 + e2e | Nom « Kingdom Hearts Birth by Sleep ». Logique activée |
| Jak 3 | Blake645/Archipelago 2.1.0 | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ 8/8 + e2e | Logique activée |
| The Legend of Zelda: Phantom Hourglass | carrotinator/Archipelago ph-v0.10.1 | ✅ | ✅ | ✅ | ✅ | ✅ (adaptateur) | ✅ 4/4 aléatoires + 5/5 yaml de Romain + e2e | Nom « The Legend of Zelda - Phantom Hourglass ». Adaptateur : entrées de `slot_data["er_pairings"]` connectées, règles de clés du générateur (pas la variante prudente d'UT). Logique activée |
| Pokémon Platinum | ljtpetersen/platinum_archipelago v0.2.2 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ + e2e | Nom « Pokemon Platinum ». Beaucoup d'options aléatoires ne génèrent pas. Logique activée |
| Pokémon Black and White | BlastSlimey/PokemonBWAP 0.3.37 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ + e2e | Nom « Pokemon Black and White ». Logique activée |
| PokéPark Wii: Pikachu's Adventure | Mekurushi/Archipelago_Pokepark 1.2.8 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ 5/5 aléatoires + 6/6 yaml de Romain + e2e | Nom « PokePark ». Stub `dolphin_memory_engine`. Pas d'adaptateur nécessaire. Logique activée |
| Ratchet & Clank 2 | evilwb/APRac2 v0.6.4 | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ + e2e | Pas de manifeste. Logique activée |
| Ratchet & Clank 3 | Taoshix/Archipelago-RaC3 v0.6.0 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ + e2e | Nom « Ratchet and Clank 3 ». Logique activée |
| AEMinecraft | KuroLynx/AEMinecraft v0.7.0-rc.5 (version de la room) | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ + e2e m7a (rc.5) ; 2/2 yaml de Romain + 5/5 aléatoires (0.7.0-rc.5, 2026-10-24) | Checksum de la room (`0741e682`) = rc.5 ; rc.2 à rc.4 donnent `132fdeb8` (logique coupée par D12 jusqu'au 2026-10-24). Logique activée |
| The Binding of Isaac: Repentance | NaveTK/Archipelago v0.4.3 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ + e2e | Nom « The Binding of Isaac Repentance ». Logique activée |
| Mario Kart Wii | toent/Archipelago-MKWii v0.3.1 | ✅ | ✅ | ✅ | ✅ | ✅ (adaptateur) | ✅ 5/5 + e2e | Adaptateur : coupes/persos/véhicules de départ et options depuis `slot_data`. Logique activée |
| The Legend of Zelda: Ocarina of Time | core 0.6.7 | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ 0/5 | **Logique impossible sans spoiler** : les récompenses de donjon (pierres/médaillons, y compris celle de la Poche de Link) sont des événements sans adresse placés au hasard ; ni le `slot_data` ni le serveur ne les transmettent. La régénération les place autrement → écarts dès la sphère 0, même avec les options par défaut. Niveau 1 seulement |

## Autres jeux de la room (M14, jeux core d'AP 0.6.7, joués par d'autres)

Version identique à la room vérifiée par `scripts/room_inventory.py` (voir `docs/COMPAT-room.md`). Aucun de ces mondes
ne sait se reconstruire depuis le seul `slot_data` (Satisfactory le peut, mais avec une logique fausse) : la logique demande le **yaml du joueur**
(clé `yaml` du slot). Validation : 3 seeds aux options aléatoires (`campaign.sh 3`, runs 501–503) + lot `m14`.

| Jeu | Validation | Logique | Notes |
|---|---|---|---|
| The Witness, Risk of Rain 2, Terraria, Undertale, A Short Hike, Inscryption, shapez, Raft, Civilization VI, Paint | ✅ 3/3 + e2e `m14` | activée (yaml) | |
| VVVVVV | ✅ 8/8 + e2e `m14b` | activée (yaml) | adaptateur : zones et coûts mélangés avec `multiworld.random`, rejoués depuis `slot_data` (`AreaRando`, `AreaCostRando`) |
| Overcooked! 2 | ✅ 5/5 + e2e `m14b` | activée (yaml) | adaptateur : cuisines mélangées (`shuffle_level_order`), ordre rejoué depuis `slot_data["CustomLevelOrder"]` |
| Hollow Knight | ✅ 5/5 + e2e `m14b` | activée (yaml) | adaptateur : coûts d'encoches des charmes et coûts des locations (CostSanity) tirés au hasard, rejoués depuis `slot_data` (`notch_costs`, `location_costs`) |
| Subnautica | ✅ 4/4 + e2e `m14b` | activée (yaml) | adaptateur : créatures à scanner tirées au hasard, rejouées depuis `slot_data["creatures_to_scan"]`. `creature_scan_logic` n'est pas dans le `slot_data` : le yaml doit le fixer (pas `random`) |
| Stardew Valley | ✅ 6/8 (2 retards d'un point) + e2e `m14b` | activée (yaml) | crochet sur les items reçus : Stardew ne compte dans « items de progression reçus » (mois vécus, % de progression) que les items progression *avant* le remplissage, alors qu'un item reçu est recréé depuis son nom. Chaque copie reçue prend la valeur d'une copie du pool régénéré, la plus basse d'abord. Limite : quand des copies d'un même nom diffèrent (saplings, dernier Trash Can, Qi Gems), le serveur ne dit pas laquelle a été reçue (`skip_balancing` n'est pas transmis) → retard possible d'un point de pourcentage, jamais d'avance (si la régénération reproduit le pool d'items de la génération) |
| Factorio | [!] 0/3 | non | impossible sans spoiler : le monde n'a pas de `fill_slot_data` (slot_data vide) ; les ingrédients des technologies `AP-1-xxx` sont tirés au hasard à la génération et écrits seulement dans le mod du jeu |
| Satisfactory | ✅ 8/8 + e2e `m14b` | activée (**yaml obligatoire**) | le `slot_data` n'a pas les options de placement des bâtiments (MAM, AWESOME, splitters…) : régénération yaml du joueur + `slot_data` ; sans yaml, « logique indisponible ». Adaptateur : en mode Universal Tracker le monde ouvre les paliers 1–2 du Hub sans les bâtiments exigés à la génération ; les régions sont construites comme à la génération |
| TUNIC | — | non | la room utilise une version plus récente que le core 0.6.7 (checksum différent, D12) |

Apworlds non core de la room, installés à une release dont le checksum est celui de la room (plusieurs releases
partagent souvent le même datapackage : la plus récente est prise, la version exacte de la room reste inconnue).
« Sans yaml » : Universal Tracker reconstruit le monde depuis le `slot_data` seul, la logique marche donc aussi pour
les slots des autres joueurs.

| Jeu | Source | Validation | Logique |
|---|---|---|---|
| Mario Kart Double Dash | aXu-AP/archipelago-double-dash v1.0.1 | ✅ 3/3 + e2e `m14b` sans yaml | activée, sans yaml |
| Archipeladoku | galdiuz/archipeladoku v2026.09.26 | ✅ 3/3 + e2e sans yaml | activée, sans yaml |
| Lego Star Wars: The Complete Saga | Mysteryem/Archipelago-TCS v1.4.4 | ✅ 3/3 + e2e sans yaml | activée, sans yaml |
| Outer Wilds | Ixrec/OuterWildsArchipelagoRandomizer v1.3.0 | ✅ 3/3 + e2e sans yaml | activée, sans yaml |
| Portal 2 | GlassToadstool/Portal2ArchipelagoMod 0.8.2 | ✅ 3/3 + e2e sans yaml | activée, sans yaml (dépendance `attrs` ajoutée à `bootstrap.sh`) |
| Haste | WritingHusky/haste_apworld v0.5.1 | ✅ 2/2 (+1 génération impossible) + e2e | activée (yaml) |
| Lethal Company | T0r1nn/APLC v0.7.13 | ✅ 8/8 + e2e `m14b` | activée (yaml) ; adaptateur : lune de départ (option « randomize ») reprise de l'inventaire de départ reçu (location −2), carte scraps → lunes (`modify_scrap_spawns`) reprise de `slot_data["moon_to_scrap_map"]` |

Non trouvés ou sans release `.apworld` correspondant au checksum de la room : PEAK, R.E.P.O, A Dance of Fire and Ice,
ArchipelaCode, Bloons TD6, Burnout Paradise Remastered, Clair Obscur Expedition 33, Cookie Clicker, et les jeux à
1 slot (non cherchés).

Les versions effectivement téléchargées (avec sha256) sont dans `config/apworlds.lock.yaml`.
Validation avec les vrais yamls de Romain : `validate_logic.py "<jeu>" --yaml config/players/romain/<fichier>`
(ses options, tirages aléatoires compris, sur des seeds différentes).

Résultats bruts des campagnes : `test-output/logs/campaign.summary` et `test-output/logic_validation/` (non commités).

## Jeux de la room 2026-10 (M24, D26–D27)

Apworlds à la version exacte de la room (même sha256 que le fichier du générateur, ou `source: user` : importé
depuis l'Archipelago du joueur, D27). Validation : 3 runs aux options aléatoires (campagne), puis 2 runs avec le yaml
de chaque joueur de la room (yamls gardés hors du dépôt), puis bout en bout. Un lot de 5 jeux par version `v0.2.N`.

| Jeu | Apworld | Validation | Logique | Notes |
|---|---|---|---|---|
| The Wind Waker | core 0.6.7 | ✅ aléatoires + 2/2 yaml de la room + e2e `m24a` | activée (yaml), v0.2.1 | adaptateur `_tww` (entrées depuis `slot_data`, donjons requis déduits des locations, comme TWW HD). Cartes mélangées (`randomize_charts`) : logique indisponible, le serveur n'envoie pas où mène chaque carte |
| R.E.P.O | Automagic00 0.4.4 | ✅ 3/3 + 6/6 yaml (3 joueurs) + e2e `m24a` | activée (yaml), v0.2.1 | |
| PEAK | importé (`source: user`) | ✅ 3/3 + 6/6 yaml (3 joueurs) + e2e `m24a` | activée (yaml), v0.2.1 | adaptateur `_peak` : biomes de `loot_sanity` tirés dans `set_rules`, rejoués depuis `slot_data["loot_biome_assignments"]` |
| Slime Rancher | SWCreeperKing v0.3.2.1 | ✅ 3/3 + 4/4 yaml + 2/2 sans yaml + e2e `m24a` (sans yaml) | activée, v0.2.1 | se reconstruit depuis le seul `slot_data` |
| Clair Obscur Expedition 33 | Demorck v0.4.3 | ✅ 3/3 + 4/4 yaml + e2e `m24a` | activée (yaml), v0.2.1 | une option n'a que des valeurs « random » : les yamls de test gardent sa valeur par défaut |
| ArchipelaCode | importé (`source: user`) | ✅ 3/3 + 4/4 yaml (2 joueurs) + e2e `m24b` | activée (yaml), v0.2.2 | adaptateur `_archipelacode` : problèmes tirés au hasard, rejoués depuis `slot_data["regions"]` ; le langage vient du yaml. `included_languages` est une liste de classe partagée par tous les mondes : l'adaptateur en donne une à chaque monde |
| Cookie Clicker | importé (`source: user`) | ✅ 2/2 + 4/4 yaml (2 joueurs) + e2e `m24b` | activée (yaml), v0.2.2 | sa location de victoire s'appelle « Victory location » dans le monde et « Victory Location » dans le datapackage |
| A Dance of Fire and Ice | importé (`source: user`) | ✅ 3/3 + 4/4 yaml (2 joueurs) + e2e `m24b` | activée (yaml), v0.2.2 | |
| Bloons TD6 | importé (`source: user`) | ✅ 3/3 + 4/4 yaml (2 joueurs) + 2/2 sans yaml + e2e `m24b` (sans yaml) | activée, v0.2.2 | se reconstruit depuis le seul `slot_data` |
| Blue Prince | importé (`source: user`) | ✅ 3/3 + 4/4 yaml (2 joueurs) + e2e `m24b` | activée (yaml), v0.2.2 | |
| Trackmania | SerialBoxes v1.3.2 | ✅ 3/3 + 2/2 yaml + e2e `m24c` | activée (yaml), v0.2.3 | adaptateur `_trackmania` : nombre de circuits par série tiré au hasard, rejoué depuis `slot_data["SeriesData"]` |
| Slime Rancher 2 | Rhelys v0.15.0 | ✅ 3/3 + 2/2 yaml + e2e `m24c` | activée (yaml), v0.2.3 | adaptateur `_slime_rancher_2` : checks de la boutique tirés au hasard (pris dans les locations du slot), vagues du catalogue et objectif de plorts depuis `slot_data` |
| Deep Rock Galactic | Cousinit117 0.20 | ✅ 3/3 + 2/2 yaml + e2e `m24c` | activée (yaml), v0.2.3 | adaptateur `_deep_rock_galactic` : locations retirées avec le `random` global (pièges désactivés, classes…) ; on garde celles du slot |
| The Farmer Was Replaced | seadoggie001 v0.0.9-beta | ✅ 3/3 + 2/2 yaml + e2e `m24c` | activée (yaml), v0.2.3 | adaptateur `_tfwr` : coût des cultures tiré au hasard (et écrit dans la table partagée), rejoué depuis `slot_data["crops.*"]` |
| Don't Starve Together | importé (`source: user`) | ✅ 5/5 + 2/2 yaml + e2e `m24c` | activée (yaml), v0.2.3 | adaptateur `_dont_starve_together` : boss requis (`slot_data["goal_locations"]`) et locations de recherche (celles du slot) ; crochet des items reçus : les items en trop mis dans l'inventaire de départ gardent leur classification du pool (`create_item` les ferait tous « progression ») |
