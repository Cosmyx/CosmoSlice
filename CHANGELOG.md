# Changelog — CosmoSlice (`2.3.1-5`)

CosmoSlice repose sur OrcaSlicer 2.3.1 et succède à Spyder (`spyder-2.3.1-4`). La partie **Base** reprend les changements majeurs d'OrcaSlicer de la 2.0.0 à la 2.3.1, d'après leurs notes de version, datés à la sortie officielle. La partie **Cosmyx** liste nos propres changements, datés à leur arrivée dans CosmoSlice. Chaque partie est classée en **Ajouté**, **Corrigé** et **Supprimé**, du plus récent au plus ancien : toute nouvelle entrée suit ce format, en haut de sa section.

## Base

### Ajouté

- **2025-10-05** — Nouveau système de mise à jour d'OrcaSlicer.
- **2025-10-05** — Ajout de couches de remplissage solide supplémentaires, par intervalle ou par liste de couches.
- **2025-10-05** — Nouveau système de rotation du remplissage, et multiplicateur de lignes de remplissage.
- **2025-10-05** — Nouveaux motifs de remplissage : nid d'abeille latéral, TPMS-FK et TPMS-D.
- **2025-10-05** — Nouvelles calibrations : Input Shaping et Junction Deviation. La calibration du débit est améliorée.
- **2025-10-05** — Peinture et mode extrusion de la peau floue (fuzzy skin).
- **2025-10-05** — Nouvel alignement de couture : « Aligned back ».
- **2025-10-05** — Évitement des résonances (porté de QIDI Slicer).
- **2025-10-05** — Murs RIB pour la tour de purge.
- **2025-10-05** — Lissage : en mode vase, sur les interfaces de support, et avec un réglage de vitesse du ventilateur.
- **2025-10-05** — Remappage des filaments pour les modèles déjà colorés.
- **2025-10-05** — Fenêtre d'import STEP (portée de Bambu Studio).
- **2025-10-05** — Choix du système de coordonnées dans les gizmos Déplacer, Échelle et Rotation, et nouveaux raccourcis.
- **2025-10-05** — Interface modernisée : boutons, dialogues, icônes, plateau 2D, légende et visualiseur G-code.
- **2025-03-20** — Bibliothèque de filaments globale : un preset filament peut être utilisé sur toutes les imprimantes.
- **2025-03-20** — Réglage de dépendance (imprimantes compatibles) pour les filaments et les process.
- **2025-03-20** — Sauvegarde des profils utilisateur à chaque mise à jour d'OrcaSlicer.
- **2025-03-20** — Nouveaux motifs de remplissage : 2D Lattice et Quartercubic.
- **2025-03-20** — Nouveaux styles de peau floue (bruit structuré, Perlin).
- **2025-03-20** — Ponts : plus de réglages, vitesse de ventilateur dédiée aux ponts internes, angle des ponts internes forcé.
- **2025-03-20** — Retrait sur la dernière couche du dessus, et insert de lissage (Ironing Inset).
- **2025-03-20** — Peinture de bordure, oreilles de souris (mouse ear brim) et peinture de supports arborescents verticaux.
- **2025-03-20** — Gizmos Mesure et Assemblage améliorés (portés de Bambu Studio).
- **2025-03-20** — Bordure pour les objets placés dans le trou d'un autre objet.
- **2025-03-20** — Calibration PA pattern en mode batch.
- **2025-03-20** — Perspective automatique en option sur les vues orthogonales.
- **2025-03-20** — Plateau Bambu Cool Plate SuperTack, et prise en charge des imprimantes Bambu en LAN.
- **2025-03-20** — Protocole `orcaslicer://`, et option pour ne pas charger les réglages imprimante/projet depuis un 3MF.
- **2025-03-20** — Algorithme Arachne mis à jour (PrusaSlicer 2.9).
- **2025-03-20** — Paquet Flatpak pour Linux.
- **2024-10-28** — Imprimantes multi-outils (toolchangers).
- **2024-10-28** — Pressure Advance adaptatif.
- **2024-10-28** — Calibration du débit en mode YOLO.
- **2024-10-28** — Verrouillage multi-matériaux (interlocking, porté de Cura).
- **2024-10-28** — Meilleure prise en charge des MMU avec coupe-filament (ERCF v2, Filametrix…).
- **2024-10-28** — Jupe et draft shield par objet.
- **2024-10-28** — Compensation du retrait du filament en XY et en Z (portée de PrusaSlicer).
- **2024-10-28** — Imprimantes à granulés.
- **2024-10-28** — Pente de déplacement (`travel_slope`) et temps de changement d'outil MMU.
- **2024-10-28** — Plateau Textured Cool Plate.
- **2024-10-28** — Peau floue avec modificateur.
- **2024-10-28** — Duplication d'un plateau avec ses objets.
- **2024-10-28** — Utilisation du dossier `data_dir` placé à côté de l'application, s'il existe.
- **2024-10-28** — Choix du mode furtif dans l'assistant de configuration.
- **2024-10-28** — Type de buse en acier trempé (HSN).
- **2024-06-21** — Nouvelles icônes.
- **2024-06-21** — Ouverture directe de modèles depuis Printables, Thingiverse et MakerWorld (Windows).
- **2024-06-21** — Motif de remplissage Cross Hatch, et réglage de la direction du remplissage.
- **2024-06-21** — Hauteur Z précise (Precise Z Height).
- **2024-06-21** — Connexion ESP3D pour l'impression sans fil.
- **2024-06-21** — Gestion de plusieurs imprimantes Bambu, et réduction de la purge par rétraction avec l'AMS.
- **2024-06-21** — Navigation 3D adaptée au pavé tactile, et navigateur 3D amélioré.
- **2024-06-21** — Décalage Z dans la calibration Pressure Advance.
- **2024-06-21** — Placeholders `model_name` et `plate_number`.
- **2024-06-21** — Miniatures améliorées.
- **2024-06-21** — Longueur minimale de jupe et draft shield.
- **2024-03-30** — Couture en biseau (scarf joint seam), avec un seuil de surplomb.
- **2024-03-30** — Compensation du débit sur les petites surfaces.
- **2024-03-30** — Maillage de plateau adaptatif direct (Marlin, Klipper, RRF).
- **2024-03-30** — Navigateur 3D.
- **2024-03-30** — Ordre d'impression au sein de chaque couche, et sens des parois.
- **2024-03-30** — Pontage des trous lamés (counterbore hole bridging, porté de SuperSlicer).
- **2024-03-30** — Réglage de la quantité de ponts internes.
- **2024-03-30** — Nettoyage configurable des parois courtes pour Arachne.
- **2024-03-30** — Éditeur de G-code personnalisé (porté de PrusaSlicer).
- **2024-03-30** — Alerte quand la vitesse, l'accélération ou le jerk dépasse les limites de la machine.
- **2024-03-30** — Nouveau remplissage 3D Honeycomb, réécrit.
- **2024-03-30** — Option pour activer ou désactiver le plugin réseau Bambu.
- **2024-03-30** — Connexions SimplyPrint, Obico et Flashforge 5M, et caméra IP personnalisée.
- **2024-03-30** — Éditeur d'infos projet, et renommage des plateaux.

### Corrigé

- **2025-10-05** — Les fichiers 3MF ne contiennent plus de données sensibles.
- **2025-10-05** — Gestion du G-code des mouvements en Z.
- **2025-10-05** — Mauvais modèle d'imprimante pour les Prusa MK3S et MINI.
- **2025-10-05** — Crash à l'import d'un 3MF enregistré en 2.3.1-alpha en mode géométrie seule.
- **2025-10-05** — Le remplissage rectiligne générait des trajets non optimisés.
- **2025-10-05** — L'export « Printer Config Bundle » était parfois refusé.
- **2025-10-05** — Nombreux correctifs : mode vase, jupe, ancrage du remplissage, évitement des parois, tour de purge, bordures, supports arborescents, mise à l'échelle de l'interface.
- **2025-10-05** — Faille de sécurité CVE-2024-45492 (libexpat).
- **2025-03-20** — Envoi lent des gros fichiers vers les imprimantes Bambu.
- **2025-03-20** — Crash à la réinitialisation des presets filament.
- **2025-03-20** — Mauvaise température de première couche avec la prévention du suintement en impression objet par objet.
- **2025-03-20** — Crash avec une interface de support inférieure réglée sur « same as top ».
- **2024-10-28** — Collision de la buse avec les parois pendant les déplacements, avec la couture en biseau.
- **2024-10-28** — Mode Inner/Outer/Inner avec Arachne dans certains cas limites.
- **2024-10-28** — Crash au double chargement d'un fichier G-code, et pendant la calibration PA pattern.
- **2024-10-28** — Divers bugs de la tour de purge.
- **2024-06-26** — La compensation de débit des petites surfaces ne fonctionnait plus.
- **2024-06-26** — Résultats de slicing parfois faux pour les modèles multi-matériaux sur Mac.
- **2024-06-26** — Opération miroir.
- **2024-06-26** — Échec de l'envoi de gros fichiers G-code vers PrusaLink.
- **2024-06-21** — Peau floue enfin uniforme et aléatoire (plus de motifs visibles sur l'axe Z).
- **2024-06-21** — Surface du dessus parfois prise pour un pont.
- **2024-03-30** — Temps de chargement/déchargement du filament ignoré dans l'estimation du temps.
- **2024-03-30** — Détection des surfaces du dessus dans des cas limites.

### Supprimé

- **2025-10-05** — Ancien code de vitesse en surplomb « classique ».
- **2025-10-05** — Dialogue d'erreur serveur Bambu, et connexion automatique à l'imprimante Bambu par défaut au démarrage.
- **2025-03-20** — La grille n'est plus le remplissage par défaut : Crosshatch la remplace.
- **2024-10-28** — Option `overhang_speed_classic` dépréciée. Le ralentissement des parois recourbées est activé par défaut.
- **2024-03-30** — Le ratio de débit de la couture en biseau n'est plus visible qu'en mode développeur.
- **2024-03-30** — Log réseau Bambu chiffré supprimé. Le niveau de log par défaut passe à « warning ».

## Cosmyx

### Ajouté

- **2026-10-29** — Version CosmoSlice `2.3.1-5` (version d'OrcaSlicer + numéro de patch Cosmyx) affichée dans « À propos », l'écran de démarrage et le test réseau, à la place de « 2.3.1 » et de la ligne « Cosmyx Bundle Version ». **Attention :** l'avis de nouveau build compare désormais cette version : si le dossier AppData a été créé par un build CSDEV, il affiche « CSDEV-V… → 2.3.1-5 » (la version enregistrée à sa création) à chaque lancement, jusqu'à la réinitialisation du dossier AppData ou sa désactivation dans les préférences.
- **2026-10-29** — CI : les builds sont nommés `CosmoSlice_<OS>_<version>_<commit court>` (par exemple `CosmoSlice_Windows_2.3.1-5_aa9dac8`). `just version` affiche la version.
- **2026-10-29** — L'index des profils Cosmyx (`cosmyx.json`) est généré à chaque build depuis l'arborescence des profils (`just profiles-index`), avec la date du commit comme version : chaque nouveau build réinstalle les profils Cosmyx fournis. Un nouveau preset n'a plus besoin d'entrée écrite à la main. La CI le génère avant chaque build et vérifie la copie présente dans chaque paquet.
- **2026-10-28** — Le nom CosmoSlice remplace OrcaSlicer dans les dialogues, messages, infobulles, préférences et astuces. La boîte « À propos » crédite OrcaSlicer, et les noms qui désignent l'amont ou sont enregistrés dans des fichiers sont gardés.
- **2026-10-28** — Les 76 textes renommés le sont aussi dans tous les catalogues de traduction. **Attention :** leurs traductions sont marquées à revoir (fuzzy) et s'affichent en anglais tant que chaque langue n'est pas mise à jour (`just i18n-status <langue>`).
- **2026-10-28** — L'assistant de configuration affiche CosmoSlice (texte anglais). Ses 14 autres langues restent à traduire.
- **2026-10-28** — Logo CosmoSlice sur la page d'accueil, l'assistant de configuration, l'icône de l'application macOS et les icônes de documents macOS (.3mf/.obj/.amf, .stl, .gcode). Ils sont générés depuis le SVG source, et `just ci` échoue si l'un d'eux s'en écarte. Les icônes .stl et .gcode reprennent l'icône de l'application en attendant des icônes dédiées.
- **2026-10-28** — Le plateau 3D des imprimantes Custom (MyKlipper, MyMarlin, MyRRF, MyToolChanger) affiche le logo CosmoSlice au lieu de celui d'Orca.
- **2026-10-28** — Pack de profils `spyder-2.3.1-4` : les filaments Cosmyx sont communs et disponibles sur toutes les machines Cosmyx, au lieu d'une copie par machine.
- **2026-10-28** — Les anciens noms de presets (buse 0.2, process et filaments par machine) sont reliés aux nouveaux : les presets utilisateur qui en héritent restent attachés.
- **2026-10-28** — Outillage : `just` à la racine (`just --list`) avec une image Docker CI figée pour les tests Python, le lint et les contrôles de traduction (`just i18n-check`, `just i18n-status`, `just i18n-rename`). Le lint couvre les scripts Python sous `scripts/`. Fins de ligne LF imposées pour tous les fichiers texte.
- **2026-09-03** — CI Windows : workflow de diagnostic de la signature Azure.
- **2026-04-24** — Journal Cosmyx (CosmoLogs) : les fonctions ajoutées par Cosmyx (température de lissage, presets, modèles Cosmyx…) écrivent dans leur propre fichier de log, avec le nom du preset concerné.
- **2026-04-24** — CI Windows : signature des exécutables, des DLL et de l'installeur avec Azure Trusted Signing.
- **2026-04-24** — CI : workflow de build Windows seul. Les builds sont nommés `CosmoSlice_<OS>_<version Cosmyx>` et l'installeur Windows `CosmoSlice_Windows_Installer_V<version>`.
- **2026-04-24** — Modèles de tickets GitHub propres à CosmoSlice : bug, amélioration, mise à jour de profil.
- **2026-04-17** — Le visualiseur G-code lit les températures `TL=` et `TR=` des macros personnalisées (par exemple `PREHEAT B=60 TL=215 TR=200`) pour la tête gauche et la tête droite.
- **2026-04-17** — Page « Connexion à l'imprimante » : animation d'aide propre à Cosmyx sur les machines Cosmyx.
- **2026-04-17** — Cosmyx est épinglé en tête de la liste des imprimantes de l'assistant de configuration.
- **2026-04-17** — Noms traduits des profils Cosmyx mis à jour dans toutes les langues, avec un outil de génération des fichiers I18N.
- **2026-04-14** — Index du pack Cosmyx (`Cosmyx.json`, PR #35) : les machines, process et filaments Cosmyx sont chargés par le slicer. Sans cet index, le pack fourni depuis le 2026-03-05 n'était pas chargé.
- **2026-03-05** — Pack de profils Cosmyx : Nova, Nova can-out, Nova Haute Température, Nova Double Tête, Nova Métal Céramique, SuperNova, SuperNova Double Tête et SuperNova Double Tête Métal Céramique, en buses 0.2 à 0.8, avec leurs covers, modèles et textures de plateau, filaments et process. Scripts Ztool pour générer les variantes et l'index. Le slicer ne le charge qu'à partir du 2026-04-14, quand son index est ajouté.
- **2026-03-05** — Traduction : environ 290 textes manquants ajoutés et traduits dans toutes les langues, avec des scripts de mise à jour des catalogues.
- **2026-03-05** — L'application s'appelle CosmoSlice : exécutable, titre de fenêtre, barre des tâches. L'installeur Windows la place dans `Cosmyx\OrcaSlicer`. Sur tous les systèmes, sa configuration va dans `Cosmyx/OrcaSlicer`, séparée de celle d'OrcaSlicer.
- **2026-03-05** — Logo CosmoSlice : icônes de l'application, boîte « À propos » et logos de l'interface. Images du plateau Cosmyx.
- **2026-03-05** — Écran de démarrage au logo CosmoSlice, sans la mention « Based on ».
- **2026-03-05** — Thème sombre par défaut.
- **2026-03-05** — Avis au lancement quand un nouveau build est installé, avec un bouton pour ouvrir le dossier AppData, et une option dans les préférences pour ne plus l'afficher.
- **2026-03-03** — Type de plateau « Cosmyx Textured Bed », avec ses températures de plateau dans les presets filament.
- **2026-03-03** — Sous-menu « Cosmyx 3D Models », avec le logo Cosmyx, dans le menu d'ajout : modèles de calibration double tête (Calage 1, 2 et 3 SNDT, cube bicolore), simple tête (Calage 1 Nova, Cosmyx Cube) et modèles pratiques (contrôle de tension de courroie, support de bobine), aux noms traduits. Les modèles de calibration proposent d'appliquer leurs réglages recommandés, et le Calage 3 place ses modificateurs d'après un fichier de configuration JSON. Les modèles OrcaSlicer restent disponibles.
- **2026-03-02** — Bouton « Exporter tous les fichiers G-code » : les G-code de tous les plateaux dans un dossier, en une fois. Placeholder `plate_count` pour le nom des fichiers.
- **2026-03-02** — Température de lissage (`ironing_temperature`) dans les presets filament : appliquée pendant le lissage, puis la température d'impression est rétablie. Traduite.
- **2026-03-02** — Version du bundle Cosmyx affichée dans la boîte « À propos ». Numéros successifs : `CSDEV-V0.6` puis `CSDEV-V0.7` (2026-03-02), `CSDEV-V0.8` (2026-03-03), `CSDEV-V0.9` puis `CSDEV-V1.0` (2026-03-05), `CSDEV-V1.1` (2026-04-17) et `CSDEV-V1.2` (2026-04-24), remplacé par `2.3.1-5` le 2026-10-29.
- **2026-03-02** — Traduction des noms de profils fabricant (fichiers I18N) dans l'assistant de configuration (fenêtre native et guide web), la sélection des filaments et les listes de presets.
- **2026-03-02** — Les espaces en fin de nom (preset, imprimante physique, fichier) sont retirés automatiquement au lieu de bloquer l'enregistrement.
- **2026-02-27** — Buses CHT et carbure de tungstène, avec leurs traductions.

### Corrigé

- **2026-10-29** — Tous les presets Cosmyx livrés (machines, filaments, process) portent la version de `cosmyx.json`, écrite à chaque build. Avant, une partie n'en portait pas et les autres gardaient d'anciennes valeurs disparates. Les fichiers du dépôt n'en portent plus.
- **2026-10-28** — L'icône de document macOS .3mf/.obj/.amf était un fichier corrompu.
- **2026-10-28** — L'imprimante Cosmyx Nova can-out se charge sous Linux : l'index des profils nommait son dossier avec la mauvaise casse.
- **2026-10-28** — Le G-code de démarrage de la Nova can-out chauffe, purge et essuie de nouveau : le pack importé l'avait mis sur une seule ligne, et seul le M104 s'exécutait.
- **2026-10-28** — Le plateau 3D des Cosmyx Nova affiche son logo en blanc, bleu et rouge au lieu de noir.
- **2026-10-28** — Quand on choisit un process ou un filament traduit, le bon preset est sélectionné, même modifié. Avant, c'était le premier de la liste.
- **2026-10-28** — La buse 0.2 devient une buse 0.25 (noms, fichiers, diamètres, variantes).
- **2026-10-28** — Le filament par défaut de toutes les machines Cosmyx est « Cosmyx PLA Basic @Cosmyx Nova ».
- **2026-10-28** — CI Windows : runners fixés sur windows-2022, et une erreur de build des dépendances arrête désormais la CI.
- **2026-10-28** — CI macOS : passage aux runners macos-15 avant le retrait de macos-14, avec une étape d'espace disque compatible avec ces runners.
- **2026-04-17** — Choisir un preset traduit dans l'onglet de réglages sélectionne le bon preset.
- **2026-04-17** — Entrée en double pour la Nova Double Tête.
- **2026-04-14** — L'avis de nouveau build reste affiché à chaque lancement tant que le dossier AppData n'a pas été migré, au lieu de disparaître après le premier.
- **2026-04-14** — Process et réglages filament en double dans le pack Cosmyx, et numéros de version écrasés.
- **2026-04-14** — Erreurs de compilation des catalogues de traduction (doublons en polonais et en espagnol, lituanien, format en français).
- **2026-03-02** — La version OrcaSlicer affichée est 2.3.1 au lieu de 2.3.2-dev.
- **2026-03-02** — Affichage des noms traduits dans les popups.
- **2026-02-27** — Au changement d'outil, la commande ventilateur (M106) est émise après le changement de tête, et s'applique donc à la nouvelle tête.

### Supprimé

- **2026-10-29** — **Attention :** `resources/profiles/cosmyx.json` n'est plus versionné, il est généré. Lancer `just profiles-index` avant un build C++ local : CMake s'arrête sinon.
- **2026-10-29** — Les deux derniers fichiers « 0.20mm Cosmyx Support W » (communs Nova et Métal Céramique), restés dans le pack sans être indexés depuis le 2026-10-28.
- **2026-10-28** — Process « 0.20mm Cosmyx Support W » (Nova, Nova can-out, Nova Double Tête, Nova Haute Température, Nova Métal Céramique, SuperNova, SuperNova Double Tête, SuperNova Double Tête Métal Céramique, et les deux communs Nova et Métal Céramique), absents du pack `spyder-2.3.1-4`. **Attention :** les presets utilisateur qui en héritent ne sont plus rattachés à un preset système.
- **2026-10-28** — Filaments Cosmyx ABS, Cosmyx ULTEM et Zetamix Zirconia, absents du pack `spyder-2.3.1-4`. **Attention :** les presets utilisateur qui en héritent ne sont plus rattachés à un preset système.
- **2026-10-28** — Profils des autres marques : seuls Cosmyx, Custom et OrcaFilamentLibrary sont gardés. Scripts Ztool retirés du pack. **Attention :** les imprimantes et presets système des autres marques disparaissent, et les presets utilisateur qui en héritent ne sont plus rattachés à un preset système. Recréer ces imprimantes à partir d'un profil Custom.
- **2026-10-28** — Restriction `compatible_printers` sur les filaments Cosmyx, et entrées mortes Cosmyx X1/P1S.
- **2026-10-28** — Filaments MyToolChanger et matériaux génériques par défaut des imprimantes Custom qui héritaient de presets disparus, et entrée FusRock ABS-GF absente d'OrcaFilamentLibrary.
- **2026-04-29** — Build quotidien planifié de la CI.
- **2026-04-24** — CI : builds Flatpak et validation de la documentation désactivés.
- **2026-04-24** — Lien de financement et anciens modèles de tickets d'OrcaSlicer.
- **2026-02-27** — Popup de mise à jour et menu « Vérifier les mises à jour ».
- **2026-02-27** — Choix du mode furtif (désormais forcé) et page du plugin réseau dans l'assistant de configuration.
