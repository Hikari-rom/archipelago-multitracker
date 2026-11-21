# Page Configuration en onglets — conception

Date : 2026-11-21. Composant concerné : `frontend/src/components/ConfigView.vue`, utilisé par la v2 (`/#config`,
menu Plus) et la v1 (`/v1#config`). Maquettes : artifact « Configuration — pistes de design », rangée « Piste A
retenue, au style de l'app » (PC onglets Slots et Fonctions, mobile liste des slots et réglages d'un slot).

## Pourquoi

La page est devenue très longue : une carte Room qui porte aussi quatre réglages de fonctions, puis Yamls, puis
Slots à suivre, puis Affichage, puis les apworlds et les mises à jour. Avec beaucoup de slots (la room de Romain en a
156, il en suit 22), les options se retrouvent loin, sous la liste, et « tout n'est pas vraiment rangé » (Romain).
Il n'y a pas de réglage qu'il cherche plus que les autres : « ça dépend vraiment des situations ».

Réussite :
- chaque réglage se trouve en un clic, sans faire défiler la liste des slots ;
- sur PC, un slot se règle sur sa ligne (yaml, joueur, but, fin) sans rien déplier ;
- sur téléphone, la page reste lisible et les cibles tactiles confortables ;
- la page suit le style de la v2 (thèmes Nuit et Plan) ; la v1 continue de marcher avec ses couleurs.

Anti-objectifs (échec même si « ça marche ») :
- perdre un réglage ou changer ce qu'il fait ;
- une page qui s'allonge encore avec le nombre de slots ;
- des couleurs écrites en dur qui cassent le thème Plan ou la v1.

## Décisions de Romain

- **Piste A : des onglets**, au style de l'app (v2), choisie parmi trois pistes (onglets, menu latéral, page unique
  repliable). Description et maquettes validées le 2026-11-21 (« pour moi on est good »).

## Ce que la page devient

### Haut de page

Comme la page Indices : le titre « Configuration » et, sur la même ligne, un résumé :
`22 suivis · 22 avec logique · 1 à corriger · room éveillée`. Les valeurs viennent de `summary` (déjà calculé) et de
`room.sleeping`. « à corriger » = slots suivis avec un diagnostic `warn` ou `error` ; absent quand il vaut 0.
« room endormie » s'affiche dans la couleur d'avertissement.

### Cinq onglets

| Onglet | Contenu (tout existe déjà, rien n'est retiré) |
|---|---|
| **Slots** (avec le nombre de suivis) | recherche, filtres, import des yamls, « Associer automatiquement », « Cocher ceux qui ont un yaml », la liste des slots (yaml, joueur, but, fin, diagnostics) |
| **Room** | lien de la room et « Découvrir les slots », pastilles de la room (slots, jeux, serveur, éveillée/endormie, « Réveiller la room »), « Avancé : serveur hors archipelago.gg », mot de passe, « Tester la connexion », « Réveiller automatiquement la room » |
| **Fonctions** | contenu des checks déjà faits (`scout_checked`), accessibilité chez les autres joueurs (`hints_foreign_logic`), choisir le but à la main (`goal_override`), tableau de bord de la room complète (`room_dashboard`) |
| **Affichage** (« cet appareil ») | `DisplayInfos`, jeux actifs, bandeau « Derniers reçus », page Indices |
| **App** | `UserApworldsPanel`, `UpdatePanel`, « Restaurer la configuration précédente » |

- Chaque fonction de l'onglet Fonctions garde son titre et sa description actuels, raccourcis si besoin, et porte une
  pastille qui nomme la page qu'elle change : Historique, Indices, Objectifs, « Plus › Room complète ».
- Un onglet qui demande l'attention porte un point : Slots s'il y a des slots à corriger, Room si la room dort ou si
  la découverte a échoué, App si une mise à jour est disponible (`tracker.update`, comme `UpdateBanner`).
- Les onglets sont un vrai composant d'onglets accessible (rôles tab/tabpanel, flèches clavier). Sur téléphone, la
  barre d'onglets défile horizontalement.

### Onglet Slots sur PC (≥ 700 px, le point de rupture de la v2)

- Filtres en pastilles, comme sur Indices : **Suivis** (cochés seulement, par défaut), **Toute la room**,
  **À corriger**. Plus la recherche (slot, jeu ou joueur).
- Un tableau : case « suivre » | slot (nom, jeu dessous, diagnostics dessous) | yaml | joueur | but | fin.
  - La colonne **But** n'existe que si « Choisir le but à la main » est actif ; une cellule vide (« — ») pour un
    jeu sans choix, un sélecteur par option de victoire sinon (plusieurs empilés si le jeu en a plusieurs), et
    « Lecture des conditions de victoire… » pendant le chargement.
  - La case **Fin** n'existe que pour les jeux avec logique (comme aujourd'hui).
  - Yaml, joueur, but et fin ne s'affichent que pour un slot coché (comme aujourd'hui).
  - La case de l'en-tête coche/décoche les slots affichés (remplace « Cocher les N affichés » / « Décocher les
    affichés »).
- Le tableau a une hauteur bornée et défile dans son cadre, en-tête collé en haut (comme aujourd'hui
  `max-h-[min(60vh,36rem)]`).

### Onglet Slots sur téléphone (< 700 px)

- Les mêmes filtres (la rangée de pastilles défile) et la recherche.
- Une ligne compacte par slot : case « suivre », nom, jeu, puis une ligne courte (yaml sans `config/players/`,
  « fin ✓ ») ou l'avertissement principal en couleur.
- Toucher la ligne (hors case) ouvre un **panneau par le bas** avec les réglages du slot : suivi, diagnostics, yaml,
  joueur, but (si actif), fin (si jeu avec logique), et un bouton OK. Les changements y sont immédiats dans le
  brouillon de la page ; OK ferme seulement.

### Enregistrer

- Une **barre flottante** en bas (au-dessus de la barre de navigation mobile de la v2) : « Changements non
  enregistrés », Annuler, Enregistrer. Elle n'apparaît que s'il y a un changement par rapport à la configuration
  chargée, sur tous les onglets. Le bouton Enregistrer garde les conditions de `canSave`.
- « Annuler » remet la page dans l'état chargé (aujourd'hui il revient au tableau de bord ; la barre remplace ce
  rôle). Pour quitter la page, la navigation habituelle suffit.
- Erreur d'enregistrement : dans la barre, qui reste affichée.
- Après un enregistrement réussi : même comportement qu'aujourd'hui (retour au tableau de bord).
- Les réglages de l'onglet **Affichage** restent appliqués tout de suite (localStorage) et ne comptent pas comme
  changements à enregistrer ; l'onglet le dit en une ligne.

### Onglet ouvert à l'arrivée

- Pas de slot configuré (première installation) : **Room**. Dans ce cas la barre d'enregistrement est toujours
  visible (dès que `canSave`), puisque tout est nouveau.
- Lien `#config?room=…` : **Room**.
- Bouton « Voir » du bandeau de mise à jour (`UpdateBanner`) : **App**.
- Sinon : **Slots**.
- L'onglet choisi s'écrit dans l'adresse (`#config/slots`, `#config/room`, `#config/fonctions`,
  `#config/affichage`, `#config/app`) pour qu'un lien ou un rechargement y revienne ; `#config` seul et
  `#config?room=…` gardent leur sens actuel.

## Contraintes

- Couleurs uniquement par les variables du thème (`bg-card`, `text-muted-foreground`, `border`, `text-primary`,
  `bg-warn`…), pour que Nuit, Plan et la v1 suivent. Les maquettes en Nuit ne sont qu'un exemple de rendu.
- Aucun changement de backend ni d'API : mêmes appels (`getConfig`, `discover`, `testConnection`, `uploadYaml`,
  `putConfig`, `restoreConfig`, `getGoalOptions`), même corps de `PUT /api/config`.
- Interface en français ; noms d'items, de jeux et d'options jamais traduits.
- Les attributs utilisés par les tests et la capture d'écran (`data-slot-list`, `data-goal-needs`, `data-goal-choice`,
  `data-goal-loading`, `data-active-mode`, `data-ticker-style`, `data-hints-layout`, `data-display-infos`) restent,
  ou les tests sont mis à jour en même temps.
- Tests vitest dans `frontend/tests/` (`configview.test.ts`) : chaque onglet, la barre d'enregistrement (apparaît,
  Annuler remet l'état, Enregistrer envoie le même corps qu'avant), l'onglet à l'arrivée, le panneau mobile.
  `npm test && npm run build`, puis captures PC et mobile, Nuit et Plan, de l'app qui tourne.

## Choix laissés au constructeur ou faits sans Romain (mes choix)

- Le sélecteur « Tous les jeux » disparaît : la recherche porte aussi sur le jeu. (mon choix)
- « Cocher ceux qui ont un yaml » reste un bouton de l'onglet Slots, à côté de l'import. (mon choix)
- La barre dit « Changements non enregistrés » sans les compter. (mon choix ; un compte est un plus, pas un dû)
- Pas d'avertissement en quittant la page avec des changements non enregistrés (comme aujourd'hui). (mon choix)
- « Il y a un changement » = le corps de `PUT /api/config` construit depuis la page diffère de celui construit depuis
  la configuration chargée (mot de passe saisi ou « effacer » coché compris). Conséquence voulue : une association
  automatique faite à l'ouverture (`autoAssociate`) fait apparaître la barre, puisqu'elle n'est prise en compte
  qu'une fois enregistrée ; des slots découverts mais non cochés ne la font pas apparaître. (mon choix)
- L'adresse `#config/<onglet>` demande d'élargir la reconnaissance de la vue dans `stores/tracker.ts` et
  `lib/config.ts` (`roomFromLocation`) ; `UpdateBanner` ouvre `#config/app`.
- Découpage en sous-composants (un par onglet, plus le panneau mobile), structure du brouillon et calcul de « il y a
  un changement » : au constructeur. Le panneau mobile peut reprendre `DialogRoot` de reka-ui comme `DetailSheet`.
- La v1 reçoit la même page (le composant est partagé) ; elle n'a pas de barre de navigation en bas, la barre
  d'enregistrement s'y pose donc en bas de l'écran.

## Hors périmètre

- Nouveaux réglages, changement de ce que fait un réglage, backend.
- Le reste de l'app (Indices, Objectifs, tableau de bord…).
