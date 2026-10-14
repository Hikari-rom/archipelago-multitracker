# Brief pour Claude Design : refonte de l'affichage de l'Archipelago Multitracker

> À coller tel quel dans Claude Design, avec les captures de l'app actuelle en pièces jointes
> (`test-output/design/captures/` ou `test-output/design/captures-app-actuelle.zip`, liste en fin de document).
> Mis à jour le 2026-10-14 : Historique, mode compact, jeu actif choisi à la main et bouton maison existent
> maintenant dans une première version fonctionnelle, à redessiner ; il reste à créer le fond étoilé et les thèmes.

---

Tu es designer produit. Je veux refaire l'affichage d'une petite app web que j'utilise tous les jours. Je ne sais pas
encore quelle direction visuelle je veux : **ton premier travail est de m'aider à choisir**, en me posant les bonnes
questions et en me montrant des directions contrastées. Ensuite seulement, tu feras des maquettes détaillées dans la
direction retenue.

## 1. Le contexte

**Archipelago** est un randomizer multi-jeux : plusieurs jeux vidéo (Zelda, Celeste, Kingdom Hearts, Pokémon…) sont
mélangés dans un même « multiworld ». Les objets d'un jeu sont cachés dans les autres jeux. Quand je fouille un
endroit d'un jeu (un **check**, ou une **location**), je peux y trouver un **item** pour un autre jeu, le mien ou celui
d'un autre joueur, et inversement.

Je joue **22 jeux en parallèle** dans la même partie (une **room** sur archipelago.gg), avec des amis qui ont leurs
propres jeux. Chaque jeu est un **slot**. Mon app répond, jeu par jeu, à une seule question :

> **« Dans quel jeu est-ce que je peux avancer maintenant, et combien de checks m'y attendent ? »**

Un check est **« en logique »** quand les items que j'ai déjà reçus permettent de l'atteindre. L'app le calcule sans
jamais rien dévoiler du contenu des checks non faits (« zéro spoiler »).

**Comment je l'utilise** :
- Sur un écran d'ordinateur, ouverte en permanence à côté du jeu auquel je joue. Je jette un œil pour voir ce que
  je viens de recevoir et décider du prochain jeu.
- Sur mon téléphone, pour voir rapidement où j'en suis.
- L'app tourne sur un Raspberry Pi chez moi. C'est un outil perso, utilisé par moi et parfois mes amis : pas de
  marketing, pas d'onboarding, pas de compte.

## 2. Le vocabulaire et les données disponibles

Une maquette ne doit montrer **que ces données** : l'app n'en a pas d'autres.

**Par slot (jeu)** :
- nom du jeu (souvent long et **jamais traduit** : « The Legend of Zelda - Phantom Hourglass »,
  « Kingdom Hearts Birth by Sleep », « Spicy Meatball Overdrive ») ;
- nom du slot (`romain_celeste`) et éventuellement le joueur à qui il appartient (si on suit plusieurs joueurs) ;
- état de connexion : connecté, en connexion, déconnecté, erreur ;
- checks faits / total, et restants (ex. 42 / 729) : de quelques dizaines à plus de 700 selon le jeu ;
- **nombre de checks en logique** (ex. 14), plus un état « logique indisponible pour ce jeu », « en calcul », ou un
  avertissement (« options aléatoires dans le yaml, logique peut-être approximative ») ;
- items reçus, dont **nouveaux depuis ma dernière visite**, avec un bouton « Marquer comme vu » ;
- hints : nombre de mes items localisés chez les autres, nombre d'items des autres dans mon monde, et parmi eux ceux
  qui sont en logique (important : ce sont des checks utiles à faire en priorité) ;
- **but** du jeu (« 120 fraises, puis Core A ») avec des compteurs (Strawberry 1 / 120) et des étapes (faite / à
  faire / invisible pour un tracker), et un drapeau « but atteint » ;
- heure du dernier check : un jeu est **« actif »** s'il a eu un check dans les 30 dernières minutes (réglable), ou
  si je l'ai **choisi comme actif** à la main (« Actif · choisi ») ; je peux aussi retirer un jeu des actifs
  (« Plus actif ») jusqu'à son prochain check ;
- checks **envoyés aux autres** : parmi mes checks faits, combien contenaient un item pour un autre joueur ;
- en détail : la liste des **locations en logique**, groupées par région du jeu, celles qui sont hintées mises en
  avant ; la liste des items reçus (nom, de qui, depuis quel jeu, quand, catégorie : progression / utile / piège /
  normal) ; la liste des hints.

**Global** :
- totaux des jeux sélectionnés (checks faits / total, en logique, nouveaux items) ;
- fil des **derniers items reçus**, tous jeux confondus (item, pour quel jeu, de qui, il y a combien de temps) ;
- état de la room : connectée, ou **endormie** (archipelago.gg arrête une room inactive ; bouton « Réveiller
  maintenant ») ;
- état de la connexion temps réel de la page (« En direct »).

**Historique** :
- pour chacun de mes checks faits : la location, l'item qui y était (avec sa catégorie : progression / utile /
  piège / normal) et à qui il est parti (moi, ou un autre joueur et son jeu), avec l'heure à laquelle l'app l'a vu
  (« avant le suivi » pour les checks faits avant que l'app ne suive le slot) ; parfois « contenu inconnu » ;
- pour chaque item reçu : l'item, pour quel jeu, de qui et depuis quelle location (ou « inventaire de départ »),
  et quand ;
- par slot : checks faits / total, envoyés aux autres, items reçus.

Exemple de ligne : « Old Site A - Room s2 → ★ **Sand of Hours** pour romain_zeldaph (The Legend of Zelda - Phantom
Hourglass) · Celeste (Open World) (romain_celeste) · avant le suivi ».

Exemple réel d'un slot, tel que l'app le reçoit :

```json
{
  "name": "romain_celeste", "game": "Celeste (Open World)", "owner": null, "status": "connected",
  "checks": {"done": 42, "total": 729, "remaining": 687},
  "items": {"received": 1, "new": 1},
  "hints": {"mine_elsewhere": 6, "in_my_world": 0, "in_my_world_in_logic": 0},
  "goal": false, "last_check_at": 1791926335, "sent": {"known": 42, "to_others": 41},
  "logic": {"state": "ok", "count": 7, "message": null},
  "objective": {
    "summary": "120 fraises, puis Core A",
    "counters": [{"label": "Strawberry", "current": 1, "target": 120}],
    "steps": [{"label": "Finir Core A (Core A - Level Clear)", "done": false},
              {"label": "Épilogue (Granny's House Keys)", "done": false}]
  }
}
```

Exemple d'une entrée du fil des items reçus : « ★ **Sand Kingdom Power Moon** pour Spicy Meatball Overdrive
(romain_odyssey) · de romain_slayyyyyy · il y a 16 min ».

## 3. L'app actuelle (voir les captures jointes)

Une seule page avec un en-tête et plusieurs vues. En-tête : titre, serveur et lien de la room, « En direct »,
bouton **maison** (retour au tableau de bord), Configuration, Objectifs, Historique, Journal, Thème (clair / sombre /
auto).
- **Tableau de bord** : sous l'en-tête, les totaux, la barre de progression globale, le tri (Conseillé / En logique /
  % en logique), **l'affichage (Cartes / Compact)** et « Masquer les jeux terminés » ; fil des 5 derniers items
  reçus ; puis les jeux. Barre de progression à deux couleurs : **vert = checks faits, bleu = checks en logique**.
  - **Affichage Cartes** : une grille de cartes, une par jeu (3 colonnes sur grand écran, 1 sur téléphone). Le ou
    les jeux actifs sont mis en avant dans une carte pleine largeur, détails ouverts.
  - **Affichage Compact** : à gauche, une seule grande carte (le jeu actif : celui choisi à la main, sinon celui
    au check le plus récent) ; à droite, une ligne par jeu (nom, nombre en logique, barre, slot, nouveaux items,
    restants). Un clic sur une ligne en fait le jeu actif. Sur téléphone, la liste passe sous la carte.
  - Chaque carte a un bouton **« Définir comme actif »**, ou **« Plus actif »** si elle l'est déjà. Ce choix est
    mémorisé par appareil.
- **Détails d'une carte** : locations en logique par région, nouveaux items, historique des items reçus, hints
  (« Hookshot → Chest ∆ TWWHD (The Wind Waker HD) »).
- **Historique** : onglets « Checks envoyés » / « Items reçus », filtre par jeu, tableau par jeu (checks faits,
  envoyés aux autres, items reçus, avec un total ; un clic sur une ligne filtre), puis la liste complète, du plus
  récent au plus ancien, par pages de 200.
- **Objectifs** : une carte par jeu avec son but, ses compteurs et ses étapes, triées par avancement.
- **Configuration** : lien de la room, mot de passe, réveil de la room, contenu des checks faits, import de yamls,
  choix des slots suivis.
- **Journal** : logs de l'app en direct, avec filtres.

Ce qui me gêne aujourd'hui (complète avec ton propre regard sur les captures) :
- les 22 cartes se ressemblent toutes et sont longues : on scrolle beaucoup pour voir où avancer ;
- beaucoup de texte et de badges de même poids : l'info clé, le nombre de checks en logique, ne ressort pas assez ;
- l'aspect est fonctionnel mais neutre : je voudrais quelque chose de plus agréable et avec du caractère ;
- l'en-tête a 6 boutons : sur téléphone il prend un écran entier avec les totaux et le fil, et le jeu actif
  n'apparaît qu'après avoir scrollé ;
- le mode compact ressemble à un collage de l'existant : la grande carte à gauche reste très longue (détails
  ouverts), et sur téléphone la liste des jeux est tout en bas ;
- l'Historique est une longue liste de texte, difficile à parcourir ; sur téléphone, le tableau par jeu est à
  l'étroit ;
- les boutons « Définir comme actif » / « Plus actif » sont discrets et leur effet n'est pas évident.

## 4. Ce que je veux

**À créer** :
1. **Fond étoilé légèrement animé** (ciel, étoiles qui scintillent ou dérivent lentement, sans gêner la lecture),
   et **d'autres thèmes au choix** dans un **menu déroulant « Thème » en haut à droite** (il remplace le bouton
   clair / sombre / auto actuel). Propose 3 ou 4 thèmes cohérents entre eux (par exemple un ciel étoilé sombre, un
   clair, et d'autres idées liées à l'univers « archipel / multi-jeux »).

**Existe déjà en version fonctionnelle, à redessiner** (voir les captures) :
2. **La page Historique** : checks envoyés et items reçus, en entier, filtrables par jeu, avec le tableau par jeu.
3. **Le bouton maison** et la navigation en général (6 boutons dans l'en-tête aujourd'hui).
4. **Le jeu actif choisi à la main** (« Définir comme actif » / « Plus actif ») : l'activité automatique (un check
   dans les 30 dernières minutes) reste trop longtemps alors que j'ai déjà changé de jeu.
5. **Le mode compact** :
   - à gauche, une seule grande carte : le jeu actif (s'il y en a plusieurs, celui qui a le check le plus récent) ;
   - à droite, une liste compacte de tous les jeux : nom, barre de checks, nombre de checks en logique ;
   - un clic sur un jeu de la liste en fait le jeu affiché à gauche.

## 5. Contraintes

- **Implémentable** par la suite avec l'existant : Vue 3, Tailwind CSS 4, composants shadcn-vue (reka-ui), icônes
  Lucide. Couleurs en variables CSS (tokens), avec une variante par thème. Polices : Google Fonts possible, sinon
  système.
- **Interface en français.** Les noms de jeux, d'items, de locations et d'options restent dans leur langue d'origine
  (anglais) : prévois des noms longs.
- **De 1 à ~60 jeux affichés** : 22 pour moi, plus quand on suit les slots des amis (un filtre par joueur existe en
  haut de page).
- **Téléphone** (390 px de large) et grand écran (1440 px et plus). Sur téléphone, l'essentiel en haut : le jeu actif
  et où avancer.
- Sémantique des couleurs à garder lisible et distincte : **fait**, **en logique**, **hint en logique**, **nouvel
  item**, **but atteint**, **erreur / avertissement**. Les teintes peuvent changer ; la distinction doit rester nette,
  y compris pour un daltonien (ne pas reposer que sur rouge / vert).
- **Accessibilité** : contrastes WCAG AA sur tous les thèmes, y compris par-dessus le fond étoilé. L'animation du fond
  doit s'arrêter avec `prefers-reduced-motion` et rester légère : elle tourne en continu sur un téléphone, à côté
  d'un jeu.
- **Zéro spoiler** : ne jamais montrer ce qu'il y a dans un check non fait.

## 6. Comment je veux travailler avec toi

**Étape 1, m'aiguiller (ne fais pas encore de maquettes détaillées)** :
- pose-moi les questions qui t'aident vraiment à trancher (5 au maximum), avec des choix proposés ;
- propose **3 directions visuelles contrastées**. Pour chacune : un nom, l'ambiance en une phrase, la palette, la
  typographie, la façon dont le tableau de bord met en avant « où avancer », et un aperçu rapide du tableau de bord
  (grand écran) dans cette direction ;
- donne ton avis sur le mode compact, maintenant que tu vois la première version : faut-il qu'il devienne
  l'affichage par défaut, reste une option, ou autre chose (et comment il doit se comporter sur téléphone) ?

**Étape 2, une fois la direction choisie** : maquettes de
- en-tête et navigation (grand écran et téléphone) ;
- tableau de bord (grand écran et téléphone), en mode Cartes et Compact ;
- carte d'un jeu : repos, active (automatiquement / choisie à la main), détails ouverts, but atteint, logique
  indisponible, room endormie ;
- page Historique (checks envoyés, items reçus, tableau par jeu ; grand écran et téléphone) ;
- page Objectifs ;
- menu Thème, avec les 3 ou 4 thèmes.

**Étape 3, pour le passage au code** : les tokens (couleurs de chaque thème, typographie, espacements, rayons,
ombres), les états des composants et la description du fond animé (technique, vitesse, densité), pour que Claude
Code puisse l'implémenter fidèlement.

À chaque étape, propose des options plutôt qu'une seule réponse, et dis-moi ce que tu recommandes et pourquoi.

---

**Captures jointes** (app actuelle au 2026-10-14, données réelles ; l'Isaac « Actif · choisi » a été choisi à la
main pour la capture) :

| Fichier | Page |
|---|---|
| `01-tableau-de-bord-cartes-desktop-dark.png` | Tableau de bord, affichage Cartes, haut de page |
| `02-tableau-de-bord-cartes-complet-desktop-dark.png` | Le même, page entière (22 jeux) |
| `03-carte-details-ouverts-desktop-dark.png` | Carte avec détails ouverts |
| `04-tableau-de-bord-compact-desktop-dark.png` | Affichage Compact |
| `05-tableau-de-bord-compact-autre-jeu-desktop-dark.png` | Compact après un clic sur un autre jeu, page entière |
| `06-historique-checks-envoyes-desktop-dark.png` | Historique, checks envoyés, page entière |
| `07-historique-items-recus-desktop-dark.png` | Historique, items reçus |
| `08-objectifs-desktop-dark.png` | Objectifs |
| `09-journal-desktop-dark.png` | Journal |
| `10-configuration-desktop-dark.png` | Configuration |
| `11` à `14` (`-desktop-light`) | Cartes, Compact, Historique et Objectifs en thème clair |
| `15` à `23` (`-mobile-dark`) | Les mêmes pages sur téléphone (390 px) |
