# Brief pour Claude Design : refonte de l'affichage de l'Archipelago Multitracker

> À coller tel quel dans Claude Design, avec les captures de l'app actuelle en pièces jointes
> (`test-output/design/captures/`, voir la liste en fin de document).

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
- heure du dernier check : un jeu est **« actif »** s'il a eu un check dans les 30 dernières minutes (réglable) ;
- en détail : la liste des **locations en logique**, groupées par région du jeu, celles qui sont hintées mises en
  avant ; la liste des items reçus (nom, de qui, depuis quel jeu, quand, catégorie : progression / utile / piège /
  normal) ; la liste des hints.

**Global** :
- totaux des jeux sélectionnés (checks faits / total, en logique, nouveaux items) ;
- fil des **derniers items reçus**, tous jeux confondus (item, pour quel jeu, de qui, il y a combien de temps) ;
- état de la room : connectée, ou **endormie** (archipelago.gg arrête une room inactive ; bouton « Réveiller
  maintenant ») ;
- état de la connexion temps réel de la page (« En direct »).

**Prévu, pour la nouvelle page Historique** : pour chacun de mes checks faits, la location, l'item qui y était et à
qui il est parti (moi ou un autre joueur), avec l'heure quand l'app l'a vu. Aussi, par slot, le nombre de checks
envoyés aux autres.

Exemple réel d'un slot, tel que l'app le reçoit :

```json
{
  "name": "romain_celeste", "game": "Celeste (Open World)", "owner": null, "status": "connected",
  "checks": {"done": 42, "total": 729, "remaining": 687},
  "items": {"received": 1, "new": 1},
  "hints": {"mine_elsewhere": 6, "in_my_world": 0, "in_my_world_in_logic": 0},
  "goal": false, "last_check_at": 1791926335,
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

Une seule page avec un en-tête et plusieurs vues :
- **Tableau de bord** : en-tête avec les totaux, la barre de progression globale, le tri (Conseillé / En logique /
  % en logique) et « Masquer les jeux terminés » ; fil des 5 derniers items reçus ; puis une grille de cartes, une
  par jeu (3 colonnes sur grand écran, 1 sur téléphone). Le jeu actif est mis en avant dans une carte pleine
  largeur, détails ouverts. Barre de progression à deux couleurs : **vert = checks faits, bleu = checks en logique**.
- **Détails d'une carte** : locations en logique par région, items reçus, hints.
- **Objectifs** : une carte par jeu avec son but, ses compteurs et ses étapes, triées par avancement.
- **Configuration** : lien de la room, mot de passe, import de yamls, choix des slots suivis.
- **Journal** : logs de l'app en direct, avec filtres.
- Thèmes clair / sombre / auto.

Ce qui me gêne aujourd'hui (complète avec ton propre regard sur les captures) :
- les 22 cartes se ressemblent toutes et sont longues : on scrolle beaucoup pour voir où avancer ;
- beaucoup de texte et de badges de même poids : l'info clé, le nombre de checks en logique, ne ressort pas assez ;
- l'aspect est fonctionnel mais neutre : je voudrais quelque chose de plus agréable et avec du caractère.

## 4. Ce que je veux ajouter (à intégrer dans tes propositions)

1. **Fond étoilé légèrement animé** (ciel, étoiles qui scintillent ou dérivent lentement, sans gêner la lecture),
   et **d'autres thèmes au choix** dans un **menu déroulant « Thème » en haut à droite**. Propose 3 ou 4 thèmes
   cohérents entre eux (par exemple un ciel étoilé sombre, un clair, et d'autres idées liées à l'univers
   « archipel / multi-jeux »).
2. **Une page Historique** : tous mes checks envoyés et tous les items reçus, en entier, filtrables par jeu, plus
   le nombre de checks envoyés par slot (voir « Prévu » plus haut).
3. **Un bouton avec une icône maison** pour revenir au tableau de bord depuis n'importe quelle page.
4. **Choisir moi-même la carte active, et désactiver une carte active** : l'activité automatique (un check dans les
   30 dernières minutes) reste trop longtemps alors que j'ai déjà changé de jeu.
5. **Un mode « compact »** à étudier :
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
- donne ton avis sur le mode compact : faut-il qu'il devienne l'affichage par défaut, une option, ou autre chose ?

**Étape 2, une fois la direction choisie** : maquettes de
- tableau de bord (grand écran et téléphone), en mode normal et compact ;
- carte d'un jeu : repos, active, détails ouverts, but atteint, logique indisponible, room endormie ;
- page Historique ;
- page Objectifs ;
- menu Thème, avec les 3 ou 4 thèmes.

**Étape 3, pour le passage au code** : les tokens (couleurs de chaque thème, typographie, espacements, rayons,
ombres), les états des composants et la description du fond animé (technique, vitesse, densité), pour que Claude
Code puisse l'implémenter fidèlement.

À chaque étape, propose des options plutôt qu'une seule réponse, et dis-moi ce que tu recommandes et pourquoi.

---

**Captures jointes** (app actuelle, données réelles) :

| Fichier | Page |
|---|---|
| `01-tableau-de-bord-desktop-dark.png` | Tableau de bord, haut de page, sombre |
| `02-tableau-de-bord-complet-desktop-dark.png` | Tableau de bord, page entière (22 jeux), sombre |
| `03-carte-details-ouverts-desktop-dark.png` | Carte avec détails ouverts |
| `04-objectifs-desktop-dark.png`, `08-objectifs-desktop-light.png` | Objectifs, sombre et clair |
| `05-journal-desktop-dark.png` | Journal |
| `06-configuration-desktop-dark.png` | Configuration |
| `07-tableau-de-bord-desktop-light.png` | Tableau de bord, clair |
| `09` à `13` (`-mobile-dark`) | Les mêmes pages sur téléphone |
