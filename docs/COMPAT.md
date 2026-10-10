# Compatibilité des jeux

Archipelago **0.6.7** (sources), Universal Tracker **Tracker_v0.3.0**, sur Raspberry Pi 5 (aarch64, Python 3.13).

Colonnes :
- **se charge** : le monde s'enregistre sous son nom de jeu (`scripts/check_apworlds.py`).
- **génère** : génération solo headless depuis le template d'options par défaut (`scripts/testenv/solo_check.py`).
- **niveau 1** : suivi générique (items, checks, hints, but) validé contre le serveur local.
- **UT sans yaml** : le monde déclare `ut_can_gen_without_yaml` (régénération à partir de `slot_data` seul).
- **UT avec yaml** : la logique fonctionne en régénérant le monde depuis le yaml du joueur.
- **validé** : comparaison de référence + bout en bout (voir M5/M7).

Légende : ✅ oui · ❌ non · ⏳ pas encore testé · — sans objet

| Jeu | Version apworld | Se charge sur 0.6.7 | Génère en headless | Niveau 1 OK | UT sans yaml | UT avec yaml | Validé par test | Notes |
|---|---|---|---|---|---|---|---|---|
| Celeste (Open World) | core 0.6.7 | ✅ | ✅ | ⏳ | ❌ | ⏳ | ⏳ | Pas d'`interpret_slot_data` : yaml nécessaire |
| Kingdom Hearts 2 | core 0.6.7 | ✅ | ✅ | ⏳ | ❌ | ⏳ | ⏳ | Pas d'`interpret_slot_data` : yaml nécessaire |
| Jak and Daxter: The Precursor Legacy | core 0.6.7 | ✅ | ✅ | ⏳ | ❌ | ⏳ | ⏳ | Pas d'`interpret_slot_data` : yaml nécessaire |
| The Wind Waker HD | Teotia444/twwhd-apworld v1.0.2-beta | ✅ | ✅ | ⏳ | ❌ | ⏳ | ⏳ | Que des releases « beta ». Pas de manifeste `archipelago.json` (avertissement AP). Le core a aussi « The Wind Waker » (GameCube), jeu distinct |
| Super Mario 64 (sm64ex) | core 0.6.7 | ✅ | ✅ | ⏳ | ❌ | ⏳ | ⏳ | |
| Super Mario Odyssey | mdietz94/smo_archipelago v1.5.3 | ✅ | ✅ | ⏳ | ❌ | ⏳ | ⏳ | S'enregistre sous le nom **« Spicy Meatball Overdrive »** (fichier `meatballs.apworld`). A un `interpret_slot_data` |
| Ori and the Blind Forest | c-ostic/Archipelago v0.4.2 | ✅ | ✅ | ⏳ | ❌ | ⏳ | ⏳ | |
| Ori and the Will of the Wisps | Satisha10/APwotw_release v0.6.5 | ✅ | ✅ | ⏳ | ✅ | ⏳ | ⏳ | |
| Balatro | BurndiL/BalatroAP v0.1.9f | ✅ | ✅ | ⏳ | ❌ | ⏳ | ⏳ | |
| Slay the Spire | cjmang/StS-AP-World 2.3.5 | ✅ | ✅ | ⏳ | ✅ | ⏳ | ⏳ | |
| Kingdom Hearts: Birth by Sleep Final Mix | gaithernOrg/ArchipelagoKHBBS 0.2.0 | ✅ | ✅ | ⏳ | ❌ | ⏳ | ⏳ | S'enregistre sous « Kingdom Hearts Birth by Sleep » |
| Jak 3 | Blake645/Archipelago 2.1.0 | ✅ | ✅ | ⏳ | ❌ | ⏳ | ⏳ | |
| The Legend of Zelda: Phantom Hourglass | carrotinator/Archipelago ph-v0.10.1 | ✅ | ✅ | ⏳ | ✅ | ⏳ | ⏳ | S'enregistre sous « The Legend of Zelda - Phantom Hourglass » |
| Pokémon Platinum | ljtpetersen/platinum_archipelago v0.2.2 | ✅ | ✅ | ⏳ | ✅ | ⏳ | ⏳ | S'enregistre sous « Pokemon Platinum » |
| Pokémon Black and White | BlastSlimey/PokemonBWAP 0.3.37 | ✅ | ✅ | ⏳ | ✅ | ⏳ | ⏳ | S'enregistre sous « Pokemon Black and White » |
| PokéPark Wii: Pikachu's Adventure | Mekurushi/Archipelago_Pokepark 1.2.8 | ✅ | ✅ | ⏳ | ✅ | ⏳ | ⏳ | S'enregistre sous « PokePark ». Importe `dolphin_memory_engine` au chargement : stub dans `backend/ap_stubs/` |
| Ratchet & Clank 2 | evilwb/APRac2 v0.6.4 | ✅ | ✅ | ⏳ | ❌ | ⏳ | ⏳ | Pas de manifeste `archipelago.json` |
| Ratchet & Clank 3 | Taoshix/Archipelago-RaC3 v0.6.0 | ✅ | ✅ | ⏳ | ✅ | ⏳ | ⏳ | S'enregistre sous « Ratchet and Clank 3 » |
| AEMinecraft | KuroLynx/AEMinecraft v0.6.2 | ✅ | ✅ | ⏳ | ❌ | ⏳ | ⏳ | Dernière release = v0.7.0-rc.1 (prerelease), on reste sur v0.6.2 comme demandé |
| The Binding of Isaac: Repentance | NaveTK/Archipelago v0.4.3 | ✅ | ✅ | ⏳ | ✅ | ⏳ | ⏳ | S'enregistre sous « The Binding of Isaac Repentance » |
| Mario Kart Wii | toent/Archipelago-MKWii v0.3.1 | ✅ | ✅ | ⏳ | ✅ | ⏳ | ⏳ | |
| The Legend of Zelda: Ocarina of Time | core 0.6.7 | ✅ | ✅ | ⏳ | ❌ | ⏳ | ⏳ | En dernier |

Les versions effectivement téléchargées (avec sha256) sont dans `config/apworlds.lock.yaml`.
