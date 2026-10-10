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
| Celeste (Open World) | core 0.6.7 | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ 10/10 seeds + e2e | Yaml nécessaire. Logique activée |
| Kingdom Hearts 2 | core 0.6.7 | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ 5/5 + e2e | Yaml nécessaire. Logique activée |
| Jak and Daxter: The Precursor Legacy | core 0.6.7 | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ 5/5 + e2e | Yaml nécessaire. Logique activée |
| The Wind Waker HD | Teotia444/twwhd-apworld v1.0.2-beta | ✅ | ✅ | ✅ | ❌ | ✅ (adaptateur) | ✅ 7/7 + e2e | Adaptateur : entrées depuis `slot_data`, donjons requis déduits des locations. Releases « beta » uniquement, pas de manifeste. Distinct de « The Wind Waker » (core) |
| Super Mario 64 (sm64ex) | core 0.6.7 | ✅ | ✅ | ✅ | ❌ | ✅ (adaptateur) | ✅ 6/6 + e2e | Adaptateur : `AreaRando` du `slot_data`. Logique activée |
| Super Mario Odyssey | mdietz94/smo_archipelago v1.5.3 | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ 5/5 comparables + e2e | Nom de jeu **« Spicy Meatball Overdrive »**. Sa génération n'est pas reproductible d'un process à l'autre (ordre de remplissage) : certains runs de validation sont « non comparables », sans effet sur la logique. Logique activée |
| Ori and the Blind Forest | c-ostic/Archipelago v0.4.2 | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ 8/8 + e2e | Logique activée |
| Ori and the Will of the Wisps | Satisha10/APwotw_release v0.6.5 | ✅ | ✅ | ✅ | ✅ (incomplet) | ⚠️ yaml + slot_data | ⚠️ 3/4 | Le `slot_data` ne couvre pas toutes les options : régénération depuis le yaml + `slot_data`. Adaptateurs : bug du spawn (coût des portes à keystones faux, aussi dans UT) et « Spawn item » en double. Reste une surestimation (événements de combat) sur 1 seed : logique désactivée |
| Balatro | BurndiL/BalatroAP v0.1.9f | ✅ | ✅ | ✅ | ❌ | ✅ (adaptateur) | ⚠️ 5/5 seeds, e2e à faire | Adaptateur : decks, mises et lots de jokers rejoués depuis `slot_data`. Logique pas encore activée |
| Slay the Spire | cjmang/StS-AP-World 2.3.5 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ + e2e | Logique activée |
| Kingdom Hearts: Birth by Sleep Final Mix | gaithernOrg/ArchipelagoKHBBS 0.2.0 | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ 8/8 + e2e | Nom « Kingdom Hearts Birth by Sleep ». Logique activée |
| Jak 3 | Blake645/Archipelago 2.1.0 | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ 8/8 + e2e | Logique activée |
| The Legend of Zelda: Phantom Hourglass | carrotinator/Archipelago ph-v0.10.1 | ✅ | ✅ | ✅ | ✅ | ✅ (adaptateur) | ⚠️ 4/4 comparables, e2e à faire | Nom « The Legend of Zelda - Phantom Hourglass ». Adaptateur : entrées de `slot_data["er_pairings"]` connectées, règles de clés du générateur (pas la variante prudente d'UT). Logique pas encore activée |
| Pokémon Platinum | ljtpetersen/platinum_archipelago v0.2.2 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ + e2e | Nom « Pokemon Platinum ». Beaucoup d'options aléatoires ne génèrent pas. Logique activée |
| Pokémon Black and White | BlastSlimey/PokemonBWAP 0.3.37 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ + e2e | Nom « Pokemon Black and White ». Logique activée |
| PokéPark Wii: Pikachu's Adventure | Mekurushi/Archipelago_Pokepark 1.2.8 | ✅ | ✅ | ✅ | ✅ | ⏳ | ⏳ | Nom « PokePark ». Stub `dolphin_memory_engine`. En cours d'analyse |
| Ratchet & Clank 2 | evilwb/APRac2 v0.6.4 | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ + e2e | Pas de manifeste. Logique activée |
| Ratchet & Clank 3 | Taoshix/Archipelago-RaC3 v0.6.0 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ + e2e | Nom « Ratchet and Clank 3 ». Logique activée |
| AEMinecraft | KuroLynx/AEMinecraft v0.6.2 | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ + e2e | v0.7.0-rc.1 (prerelease) ignorée. Logique activée |
| The Binding of Isaac: Repentance | NaveTK/Archipelago v0.4.3 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ + e2e | Nom « The Binding of Isaac Repentance ». Logique activée |
| Mario Kart Wii | toent/Archipelago-MKWii v0.3.1 | ✅ | ✅ | ✅ | ✅ | ✅ (adaptateur) | ✅ 5/5 + e2e | Adaptateur : coupes/persos/véhicules de départ et options depuis `slot_data`. Logique activée |
| The Legend of Zelda: Ocarina of Time | core 0.6.7 | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ 0/5 | **Logique impossible sans spoiler** : les récompenses de donjon (pierres/médaillons, y compris celle de la Poche de Link) sont des événements sans adresse placés au hasard ; ni le `slot_data` ni le serveur ne les transmettent. La régénération les place autrement → écarts dès la sphère 0, même avec les options par défaut. Niveau 1 seulement |

Les versions effectivement téléchargées (avec sha256) sont dans `config/apworlds.lock.yaml`.
Résultats bruts des campagnes : `test-output/logs/campaign.summary` et `test-output/logic_validation/` (non commités).
