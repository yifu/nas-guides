@header Guide NAS · Synology DS225+

@title Synology DS225+ : installation et configuration

@subtitle Mise en service d'un DS225+ à deux disques : DSM, pool SHR, volume Btrfs chiffré, snapshots, et dossier partagé dédié à Time Machine pour un ou plusieurs Mac. Écrit pour DSM 7.4. Version du 22 octobre 2026.

Ce guide suit l'ordre réel de la mise en service, du carton jusqu'à la première sauvegarde Time Machine vérifiée. Les menus sont donnés avec leurs libellés anglais, ceux de l'aide officielle de Synology : l'interface française en est une traduction directe (Control Panel = Panneau de configuration, Storage Manager = Gestionnaire de stockage, Shared Folder = Dossier partagé, File Services = Services de fichiers).

Les quatre questions de départ, et où se trouve la réponse :

|= 150.0 251.9 80.0 header
| Question | Réponse courte | Section |
| SHR ou RAID 1 ? | SHR. Avec deux disques identiques, même protection et même capacité que RAID 1, et plus de souplesse pour changer de disques plus tard. | 4 |
| Quand chiffrer ? | À la création du volume, et seulement là : un volume existant ne se chiffre pas après coup. | 5 |
| Snapshots ? | Paquet Snapshot Replication, planifié par dossier partagé, avec une partie immuable pour les données. | 7 |
| Dossier Time Machine ? | Dossier dédié, sans corbeille ni chiffrement de dossier, quota, un compte DSM par Mac, SMB3 et annonce Bonjour. | 8 |

!flow
Matériel | Disques CMR, branchement sur le port 2,5 GbE, onduleur si possible.
Installation de DSM | Assistant web, compte administrateur, mises à jour.
Test des disques | Test S.M.A.R.T. étendu sur chaque disque, avant d'y écrire quoi que ce soit.
Pool de stockage SHR | Les deux disques, une tolérance de panne d'un disque.
*Volume Btrfs chiffré | C'est ici, et seulement ici, que se décide le chiffrement.
Réglages de base | Notifications par e-mail, sécurité, nettoyage des données (scrubbing).
Snapshots | Snapshot Replication, planification et rétention par dossier.
Dossier Time Machine | Dossier, compte, quota, SMB, Bonjour.
Côté Mac | Ajout du disque, chiffrement de la sauvegarde, vérification.

!! **Ce qui ne se rattrape pas.** La plupart des étapes se corrigent après coup. Quatre ne se corrigent pas, et les encadrés rouges les signalent dans leur section.
!! **Chiffrement du volume** (section 5) : il se choisit à la création du volume et ne s'annule jamais. Le changer plus tard veut dire vider le NAS, supprimer le volume et le recréer.
!! **Clé de récupération et mot de passe du coffre** (section 5) : si les deux sont perdus le jour où le coffre est inaccessible, les données du volume sont perdues pour de bon.
!! **Mot de passe de chiffrement Time Machine** (section 8) : sans lui, les sauvegardes du Mac sont illisibles, même pour toi.
!! **Snapshots immuables** (section 7) : pendant leur période de protection, personne ne peut les supprimer, pas même l'administrateur. Une période trop longue bloque l'espace disque qu'ils occupent.

# 1. Matériel

## 1.1 Le DS225+ en bref

Processeur Intel Celeron J4125 (4 cœurs, instructions AES-NI), 2 Go de mémoire DDR4 extensibles à 6 Go par une barrette Synology de 4 Go, deux baies SATA 3,5 ou 2,5 pouces, un port 1 GbE et un port 2,5 GbE, deux ports USB 3.2 Gen 1. Il gère SHR, RAID 1, Btrfs, le chiffrement de volume et les snapshots immuables. Pour des sauvegardes Time Machine et des fichiers de famille, les 2 Go d'origine suffisent : la barrette de 4 Go n'est utile que pour la reconnaissance des visages de Synology Photos ou des conteneurs.

## 1.2 Les disques

Depuis DSM 7.3, les modèles Plus de 2025, dont le DS225+, acceptent à nouveau des disques d'autres marques pour créer un pool de stockage : les premiers firmwares de cette gamme le refusaient. Synology ne garantit toutefois que les disques de sa liste de compatibilité, et DSM peut afficher un avertissement pour les autres. Les deux choix raisonnables :

- Synology HAT3300 (gamme Plus), la voie sans surprise côté DSM.

- Un disque NAS d'une autre marque en technologie **CMR** (WD Red Plus, Seagate IronWolf, Toshiba N300). Éviter les disques **SMR** (enregistrement magnétique en tuiles), dont la reconstruction après une panne est très lente : c'est le cas des WD Red sans « Plus » de 2 à 6 To.

Deux disques de même capacité : avec SHR, toute capacité au-delà de celle du plus petit disque reste inutilisée tant qu'il n'y en a que deux. Pour la taille, compter la somme des Mac à sauvegarder multipliée par deux ou trois (section 8.1), plus les fichiers que la famille stockera directement sur le NAS, plus une marge pour les snapshots.

## 1.3 À côté du NAS

- Un câble RJ45 vers la box, sur le port **2,5 GbE** si la box en a un aussi, sinon n'importe lequel des deux.

- Un onduleur (UPS) avec port USB, conseillé : DSM sait s'arrêter proprement quand la batterie faiblit (section 6.4). Une coupure brutale pendant une écriture est le pire moment pour un système de fichiers.

- Un emplacement aéré, pas dans un placard fermé. Le NAS reste allumé en permanence.

# 2. Installation de DSM

## 2.1 Montage et branchement

Insérer les deux disques dans les tiroirs en façade (fixation sans outil pour les disques 3,5 pouces, vis fournies pour les 2,5 pouces), brancher le câble réseau et l'alimentation, puis appuyer sur le bouton de mise en marche. Le premier démarrage prend quelques minutes, jusqu'au bip et au voyant STATUS fixe.

> **Adresse IP :** dans l'interface de la box, réserver dès maintenant une adresse IP fixe pour le NAS (bail DHCP statique, associé à son adresse MAC, visible dans la liste des appareils connectés). C'est plus simple que de fixer l'adresse dans DSM, et la box reste seule maître du plan d'adressage.

::: Livebox 6 et 7 (Orange)

Ouvrir `http://192.168.1.1` depuis un appareil du réseau. Le mot de passe administrateur est, par défaut, fait des 8 premiers caractères de la clé Wi-Fi imprimée sous la box (sauf s'il a été changé). Puis :

- **Paramètres avancés** (en bas de page), **Réseau**, onglet **DHCP**.

- Section **Baux DHCP statiques** : choisir le NAS dans la liste des équipements connectés, saisir l'adresse IP, puis **Ajouter**. Si le NAS n'est pas encore branché, choisir **Équipement** en bas de la liste et saisir son adresse MAC (étiquette sous le NAS).

Réserver de préférence l'adresse que la box a déjà donnée au NAS : des utilisateurs ont vu la Livebox accepter une réservation tout en continuant d'afficher l'ancienne adresse. Si l'adresse change, redémarrer le NAS pour qu'il renouvelle son bail, puis vérifier en 2.3.

:::

## 2.2 L'assistant d'installation

Depuis un ordinateur du même réseau, ouvrir `find.synology.com` dans un navigateur. Si la page ne trouve rien, utiliser Synology Assistant (rubrique Desktop Utilities du centre de téléchargement Synology), ou taper directement l'adresse IP du NAS suivie de `:5000`, par exemple `http://192.168.1.20:5000`.

- **Installer DSM :** laisser l'assistant télécharger la dernière version depuis Internet. Il prévient que les disques seront effacés : c'est attendu, ils sont neufs.

- **Nom du NAS :** un nom court sans espace ni accent, par exemple `nas-famille`. On le retrouvera dans Finder et dans Time Machine.

- **Compte administrateur :** un nom qui n'est **pas** `admin` (DSM 7 désactive déjà le compte `admin` intégré), et un mot de passe long, rangé dans ton gestionnaire de mots de passe. Ce compte sert à administrer, pas à stocker des fichiers au quotidien.

- **Mises à jour :** choisir l'installation automatique des mises à jour importantes (correctifs de sécurité). Les mises à jour majeures restent manuelles.

- **Compte Synology et QuickConnect :** l'assistant propose de lier un compte Synology. Il n'est pas nécessaire pour ce guide : QuickConnect (accès depuis Internet par les serveurs de Synology) est désactivé en section 6.3. On peut passer cette étape.

- **Statistiques d'utilisation :** refuser l'envoi.

À la fin, l'assistant propose de créer le stockage. **Refuser pour l'instant** si c'est possible (ou fermer la fenêtre) : les disques doivent d'abord être testés (section 3).

## 2.3 Premiers réglages

- **Control Panel > Regional Options :** fuseau Europe/Paris, synchronisation de l'heure avec un serveur NTP (`pool.ntp.org` ou celui de Synology). Les noms des snapshots et l'historique Time Machine dépendent de l'heure.

- **Control Panel > Update & Restore :** vérifier que DSM est à jour, et installer la mise à jour proposée le cas échéant.

- **Control Panel > Network :** vérifier que l'adresse IP est bien celle réservée dans la box.

# 3. Tester les disques

Avec SHR sur deux disques, DSM ne fait aucune vérification automatique des disques à la création du pool (il ne le fait que pour RAID 5, RAID 6 ou SHR à plus de trois disques). Un disque défectueux à la livraison ne se verra donc qu'une fois des données dessus. Un test S.M.A.R.T. étendu lit toute la surface du disque et révèle les secteurs défectueux avant qu'ils ne gênent.

Dans **Storage Manager > HDD/SSD**, sélectionner le premier disque, ouvrir **Health Info**, puis lancer un test S.M.A.R.T. **étendu** (Extended). Faire de même pour le second : les deux tests tournent en parallèle.

> **Durée :** plusieurs heures, de l'ordre de deux heures par téraoctet. Un test lancé le soir est fini le lendemain. Ne pas créer le pool pendant le test : la création l'interrompt.

Résultat attendu : état **Healthy** (Sain) pour les deux disques, test terminé sans erreur, et aucun secteur réalloué (reallocated sectors à 0) dans les attributs S.M.A.R.T. Un disque neuf qui a déjà des secteurs réalloués se renvoie au vendeur.

# 4. Pool de stockage en SHR

## 4.1 Pourquoi SHR plutôt que RAID 1

SHR (Synology Hybrid RAID) n'est pas un niveau de RAID de plus : DSM découpe les disques en tranches de même taille, assemble chaque niveau de tranches en RAID classique (mdadm), puis réunit le tout avec LVM. Avec deux disques de même taille, il n'y a qu'une tranche : SHR revient exactement à un RAID 1 sous une couche LVM.

|= 150.0 165.0 166.9 header
| | SHR (SHR-1) | RAID 1 |
| Capacité utile avec 2 × 8 To | 8 To | 8 To |
| Panne d'un disque | Tolérée | Tolérée |
| Disques de tailles différentes | Exploite au mieux l'espace | Limité au plus petit disque |
| Agrandir avec de plus gros disques | Oui, disque par disque | Oui, disque par disque |
| Passer plus tard à un NAS plus grand | Ajout de disques simple (SHR) | Changement de type de RAID |
| Lecture par d'autres systèmes | Linux avec mdadm et LVM | Linux avec mdadm |

Les performances sont les mêmes. L'avantage de SHR se voit le jour où l'un des disques est remplacé par un plus gros, ou lors d'une migration vers un modèle à quatre baies : SHR ne demande alors rien de particulier. Synology recommande SHR pour un usage domestique, et le DS225+ le propose dans la liste des types de RAID.

## 4.2 Créer le pool

Dans **Storage Manager > Storage**, cliquer sur **Create Now**. L'assistant de première création enchaîne le pool et le volume :

- **RAID type :** SHR. L'assistant affiche « Drive fault tolerance: 1 ».

- **Disques :** cocher les deux.

- Valider. L'assistant enchaîne sur le volume (section 5).

> **Si l'assistant ne propose pas SHR :** sur les modèles Plus, SHR est disponible par défaut. Si la liste ne montre que des types RAID classiques, vérifier que le modèle est bien le DS225+ (Control Panel > Info Center) avant d'aller plus loin.

# 5. Volume Btrfs et chiffrement

## 5.1 Quand chiffrer

**Maintenant**, pendant la création du volume, avant le moindre dossier partagé. DSM 7.2 et suivants chiffrent le volume entier avec LUKS (AES en mode XTS, comme `cryptsetup` sous Linux), mais seulement à sa création : un volume existant ne peut ni être chiffré ni être déchiffré après coup. Revenir sur ce choix plus tard veut dire tout copier ailleurs, supprimer le volume, le recréer et tout recopier. Le DS225+ fait partie des modèles qui gèrent le chiffrement de volume.

## 5.2 Ce que le chiffrement protège, et ce qu'il ne protège pas

La clé de chaque volume chiffré est rangée dans un **coffre de clés** (Encryption Key Vault). Pour un NAS seul, le coffre est **local** : il est stocké sur le NAS lui-même et protégé par un mot de passe. Au démarrage, DSM ouvre le coffre et déverrouille le volume tout seul, sans rien demander.

- **Protégé :** un disque sorti du NAS. Disque défectueux renvoyé en garantie, disque revendu ou jeté, disque volé seul : sans la clé, son contenu est illisible. Avec un RAID, ce cas arrive forcément un jour, et c'est la vraie raison de chiffrer.

- **Pas protégé :** le NAS volé en entier. Il redémarre et se déverrouille seul chez le voleur, comme chez toi. Des chercheurs ont d'ailleurs montré qu'avec le coffre local, quelqu'un qui a le NAS complet entre les mains peut récupérer la clé. La seule parade est un coffre sur un serveur KMIP distant, qui doit être un autre NAS Synology : hors sujet ici.

- **Pas protégé non plus :** tout ce qui passe par le réseau (compte volé, rançongiciel sur un Mac). Le volume est déverrouillé pendant le fonctionnement. C'est le rôle des comptes, de la double authentification (section 6) et des snapshots immuables (section 7).

Le coût en performances est faible grâce aux instructions AES-NI du processeur : le réseau reste le facteur limitant. **Recommandation : chiffrer.** Ça ne coûte presque rien, et c'est impossible à ajouter plus tard.

## 5.3 Créer le volume chiffré

L'assistant de première création enchaîne sur le volume. (Pour un volume ajouté plus tard : **Storage Manager > Storage > Create > Create Volume**.)

- **Capacité :** cliquer sur **Max**. Un seul volume pour tout le pool est le plus simple.

- **Système de fichiers :** **Btrfs**. Indispensable : snapshots, quotas par dossier partagé, sommes de contrôle des données. ext4 n'offre rien de tout ça.

- **Chiffrement :** cocher **Encrypt this volume**. DSM rappelle que l'opération est irréversible.

- **Coffre de clés :** DSM demande d'activer le coffre. Choisir **Local** et définir le **mot de passe du coffre** : un mot de passe différent de celui du compte administrateur, rangé dans ton gestionnaire de mots de passe. (Le réglage se retrouve ensuite dans **Storage Manager > Storage > Global Settings > Encryption Key Vault**.)

- Valider avec **Apply**. Le navigateur télécharge aussitôt la **clé de récupération** du volume, un petit fichier.

!! **Clé de récupération et mot de passe du coffre :** si le coffre devient inaccessible (réinitialisation de DSM avec verrouillage des volumes chiffrés, déplacement des disques dans un autre NAS, coffre endommagé), le volume reste verrouillé. On le déverrouille avec la clé de récupération **ou** le mot de passe du coffre. Si les deux sont perdus, les données sont perdues, et Synology ne peut rien y faire.
!! Ranger la clé de récupération à deux endroits : dans ton gestionnaire de mots de passe (en pièce jointe) et sur une clé USB gardée ailleurs que là où se trouve le NAS. Jamais seulement sur le NAS ou sur l'ordinateur qui a servi à l'installation.

Si la clé de récupération est perdue mais que le volume est encore déverrouillé, on peut en générer une nouvelle (l'ancienne devient alors inutilisable) : **Storage Manager > Storage**, menu « ... » du volume, **Settings**, section **Recovery Key**, **Regenerate**.

L'optimisation du volume prend ensuite un moment en arrière-plan ; le NAS reste utilisable pendant ce temps.

## 5.4 Pas de chiffrement de dossier partagé

DSM propose aussi de chiffrer un dossier partagé (case « Protect this shared folder by encrypting it »). C'est une autre technique, plus ancienne (eCryptfs), avec des contraintes gênantes : noms de fichiers limités à 130 caractères depuis un Mac, pas de compression, snapshots impossibles à parcourir. Synology la déconseille pour Time Machine, et avec un volume déjà chiffré elle n'apporte rien ici. **Ne pas la cocher**, ni pour Time Machine ni pour les autres dossiers.

# 6. Réglages de base et sécurité

## 6.1 Notifications par e-mail

C'est le réglage le plus important pour un NAS installé chez quelqu'un d'autre : un disque qui lâche ne se remarque pas, puisque SHR continue de fonctionner sur l'autre. Il faut que l'alerte arrive dans ta boîte mail.

Dans **Control Panel > Notification**, onglet **Email** : activer les notifications, choisir le fournisseur de la boîte d'envoi (DSM propose les plus courants, dont Gmail et Outlook, ou un serveur SMTP quelconque), et mettre en destinataires ton adresse et celle des personnes qui utilisent le NAS. Envoyer un **message de test** et vérifier qu'il arrive, y compris dans les indésirables.

## 6.2 Vérifications régulières des disques

- **Nettoyage des données (Data Scrubbing) :** dans **Storage Manager > Storage**, menu du pool, planifier un nettoyage tous les trois mois, la nuit. Avec Btrfs et les sommes de contrôle (section 8.2), le scrubbing relit toutes les données, détecte les blocs corrompus et les répare à partir de la copie de l'autre disque.

- **Tests S.M.A.R.T. :** dans les réglages de **Storage Manager > HDD/SSD**, planifier un test rapide mensuel et un test étendu tous les trois mois, à un autre moment que le scrubbing.

## 6.3 Comptes et accès

### Séparer administration et usage quotidien

C'est le même principe que `root` et le compte utilisateur sous Linux, et il s'applique même quand la même personne utilise les deux comptes. Le compte du quotidien est celui qu'on monte dans le Finder et dont le mot de passe reste dans le trousseau du Mac : c'est donc celui qu'un logiciel malveillant sur le Mac utiliserait. S'il était administrateur :

- il aurait accès à tout, car DSM donne par défaut au groupe `administrators` la lecture et l'écriture sur tous les dossiers partagés, `TimeMachine` compris : un rançongiciel sur le Mac chiffrerait les données du NAS **et** les sauvegardes ;

- il pourrait tout défaire : supprimer les snapshots non immuables, changer les réglages, effacer des dossiers ;

- la double authentification ne le protégerait pas : elle ne s'applique qu'à la connexion web à DSM, et un partage SMB monté dans le Finder ne demande que le mot de passe.

D'où trois sortes de comptes :

|= 120.0 180.0 181.9 header
| Compte | Sert à | Droits |
| Administrateur (le tien) | Administrer DSM depuis le navigateur, rien d'autre. Jamais monté dans le Finder. | Groupe `administrators`, double authentification. |
| Quotidien (par exemple `papa`) | Déposer et consulter des fichiers sur le NAS depuis le Finder. | Groupe `users` seulement. Lecture et écriture sur les dossiers de données, rien sur `TimeMachine`. SMB, plus File Station ou Synology Photos si besoin. |
| Time Machine (`tm-macbook`…) | La sauvegarde d'un Mac, et seulement elle (8.3). | Groupe `users` seulement. Lecture et écriture sur `TimeMachine`, SMB seul. |

Si personne ne dépose de fichiers directement sur le NAS et qu'il ne sert qu'à Time Machine, le compte du quotidien est inutile : le compte administrateur et les comptes Time Machine suffisent.

### Réglages

- **Double authentification** pour le compte administrateur : menu en haut à droite, **Personal > Security > 2-Factor Authentication**, avec une application TOTP. Garder les codes de secours avec la clé de récupération.

- **Compte du quotidien :** **Control Panel > User & Group > User > Create**, groupe `users` seulement, droits sur les dossiers de données comme dans le tableau.

- **Control Panel > Security > Account :** vérifier que le blocage automatique (Auto Block) est activé : une adresse IP qui se trompe trop souvent de mot de passe est bloquée.

- **QuickConnect désactivé** (Control Panel > External Access) et **aucune redirection de port** dans la box. Le NAS n'est alors joignable que depuis le réseau local.

- **Accès à distance pour toi (facultatif) :** pour administrer le NAS depuis chez toi sans l'exposer sur Internet, installer le paquet **Tailscale** depuis le Package Center et le relier à ton compte Tailscale. Le NAS devient joignable depuis tes machines par le réseau privé de Tailscale, sans port ouvert sur la box.

- **Security Advisor :** lancer une analyse une fois tout configuré, et lire ses recommandations.

## 6.4 Alimentation

- **Control Panel > Hardware & Power > General :** activer le redémarrage automatique après une coupure de courant.

- **Onglet UPS** (si un onduleur est branché en USB) : activer la prise en charge de l'onduleur, et choisir l'arrêt du NAS au bout de quelques minutes sur batterie plutôt qu'à batterie presque vide.

- **Mise en veille des disques :** facultatif. Time Machine réveille les disques toutes les heures pendant la journée ; une mise en veille au bout de 20 minutes d'inactivité fait surtout gagner la nuit.

# 7. Snapshots

## 7.1 Principe

Un snapshot est une image en lecture seule d'un dossier partagé à un instant donné. Btrfs le prend en une fraction de seconde et ne stocke ensuite que ce qui change : tant que rien ne bouge, il ne coûte presque rien. Il protège contre la suppression accidentelle, la mauvaise modification, et le rançongiciel qui chiffre les fichiers depuis un ordinateur : un snapshot ne se modifie pas depuis le réseau, même avec le compte du propriétaire des fichiers.

Un snapshot **n'est pas une sauvegarde** : il vit sur les mêmes disques. Si le pool meurt, les snapshots meurent avec lui (section 9).

> **Snapshots immuables :** une option rend un snapshot impossible à supprimer pendant une période de protection, par qui que ce soit, administrateur compris. C'est la défense contre un attaquant qui aurait pris le compte administrateur et effacerait les snapshots avant de chiffrer les données. Synology recommande une protection de 7 à 14 jours. Contrepartie : pendant cette période, l'espace occupé par ces snapshots ne peut pas être libéré, et un dossier partagé qui a des snapshots immuables ne peut pas être supprimé.

## 7.2 Installer Snapshot Replication

**Package Center**, rechercher **Snapshot Replication**, installer. Le paquet a deux parties : Snapshots (ce qui nous intéresse) et Replication (copie vers un autre NAS Synology, hors sujet ici). Le DS225+ garde au plus 128 snapshots par dossier partagé : les réglages ci-dessous restent largement en dessous.

## 7.3 Dossiers de données

Pour chaque dossier où la famille range des fichiers (par exemple `Famille`, `Photos`), dans **Snapshot Replication > Snapshots**, sélectionner le dossier, puis :

- **Settings > Schedule :** cocher **Enable snapshot schedule**, toutes les **4 heures**. Cocher **Enable immutable snapshots**, protection **7 jours**.

- **Settings > Retention :** **Smart Retention policy**, puis **Set Rules** : tout garder 7 jours, le dernier snapshot du jour pendant 30 jours, celui de la semaine pendant 12 semaines, celui du mois pendant 12 mois, et au minimum les 10 derniers snapshots.

- **Settings > Advanced :** cocher **Make snapshot visible**. Un dossier `#snapshot` apparaît alors à la racine du partage, dans Finder : on y retrouve chaque version, en lecture seule, et on récupère un fichier par simple copie, sans passer par DSM.

> **Le compte :** 6 snapshots par jour gardés 7 jours (42), plus environ 23 quotidiens, 8 hebdomadaires et 9 mensuels : une centaine au plus, sous la limite de 128. Pour des snapshots toutes les heures, ne pas cocher l'immuabilité : 7 jours d'instantanés horaires immuables feraient 168 snapshots, au-delà de la limite.

## 7.4 Dossier Time Machine

Time Machine gère déjà son propre historique : les snapshots du NAS n'apportent rien pour retrouver une ancienne version d'un fichier du Mac. Ils servent à autre chose. La sauvegarde réseau de Time Machine est une image disque (un dossier `.sparsebundle` fait de milliers de petits fichiers), et il arrive qu'elle s'abîme, après une coupure réseau en pleine sauvegarde par exemple. Le Mac annonce alors qu'il doit créer une nouvelle sauvegarde, et tout l'historique est perdu. Avec des snapshots, on remet en place l'image de la veille, et l'historique est sauvé.

Réglages pour le dossier `TimeMachine` (créé en section 8.2) :

- **Schedule :** un snapshot par jour, à une heure où les Mac dorment (5 h par exemple). Pas d'immuabilité : en cas de manque de place, il faut pouvoir supprimer ces snapshots sans attendre.

- **Retention :** **Numbers of latest snapshots to keep**, 7.

- **Make snapshot visible :** non, inutile ici.

> **Espace :** chaque snapshot garde les blocs que Time Machine a réécrits depuis, y compris ceux des anciennes sauvegardes que le Mac élague. Prévoir de la marge sur le volume au-delà du quota du dossier (section 8.1), et regarder l'occupation réelle au bout de quelques semaines avec **Snapshot > Calculate Size**.

Pour revenir en arrière après une image abîmée : arrêter d'abord Time Machine sur le Mac concerné (décocher la sauvegarde automatique), puis **Snapshot Replication > Snapshots**, dossier `TimeMachine`, **Snapshot > Snapshot List**, choisir le snapshot de la veille et le restaurer, en acceptant de prendre un snapshot de l'état actuel avant la restauration. Réactiver ensuite Time Machine. Si l'image de la veille est elle aussi refusée, essayer la précédente : un snapshot pris pendant une sauvegarde peut capturer un état intermédiaire.

# 8. Dossier partagé Time Machine

## 8.1 Organisation et taille

Un seul dossier partagé `TimeMachine` pour tous les Mac de la maison, et **un compte DSM par Mac**. Chaque Mac crée sa propre image disque dans le dossier ; le compte dédié permet de limiter la place de chacun et de couper l'accès d'un Mac sans toucher aux autres. Ce compte ne sert qu'à Time Machine : il n'a accès à rien d'autre, et ni à DSM ni à File Station.

Deux limites, qui se complètent :

- **Quota du compte** sur le dossier `TimeMachine` : la place de ce Mac. Synology conseille **deux à trois fois** la quantité de données à sauvegarder sur le Mac (et pas la taille de son disque, si le disque est loin d'être plein). Une fois la limite atteinte, Time Machine supprime de lui-même les sauvegardes les plus anciennes.

- **Quota du dossier partagé** : la somme des quotas des comptes, pour que Time Machine ne puisse jamais remplir le volume au détriment des autres dossiers et des snapshots.

|= 160.0 110.0 211.9 header
| Mac | Données sur le Mac | Quota du compte |
| MacBook (500 Go de données) | 500 Go | 1,2 To |
| iMac (300 Go de données) | 300 Go | 800 Go |
| **Dossier `TimeMachine`** | | **2 To** (somme des deux) |

### Estimer, puis ajuster

**Avant la première sauvegarde**, lire l'espace **utilisé** sur le Mac, pas la capacité de son disque : **Réglages Système > Général > Stockage**, ou **À propos de ce Mac > Plus d'infos > Stockage**. Ce chiffre majore un peu le besoin, car il compte macOS lui-même, les caches et une partie des « Données système » (instantanés locaux, fichiers d'échange), que Time Machine ne sauvegarde pas : la marge joue en ta faveur.

Choisir le facteur selon l'usage du Mac :

- **× 2** pour des documents, des mails et quelques photos : l'historique est déjà long.

- **× 3** pour de la vidéo, une grosse bibliothèque photo souvent retouchée ou des machines virtuelles : chaque modification renvoie de gros fichiers, et l'historique se consomme vite.

**Après la première sauvegarde**, regarder ce qu'elle occupe réellement : **Control Panel > Shared Folder**, dossier `TimeMachine` (ou **Control Panel > User & Group**, compte du Mac, **Edit > Quota**, qui montre l'usage du compte). Ajuster alors le quota du compte à deux ou trois fois cette valeur, et le quota du dossier en conséquence.

> **Le quota se change à tout moment :** le relever ne casse rien, Time Machine en profite simplement pour garder un historique plus long. Un Mac dont le disque se remplit au fil des années se gère donc en relevant son quota, sans rien prévoir de démesuré au départ. Le baisser en dessous de l'occupation actuelle est en revanche à éviter : Time Machine devra supprimer d'anciennes sauvegardes pour retrouver de la place, ou échouera s'il n'en libère pas assez.

## 8.2 Créer le dossier partagé

**Control Panel > Shared Folder > Create > Create Shared Folder**, et dans l'assistant :

|= 200.0 75.0 206.9 header
| Option | Choix | Pourquoi |
| Name | `TimeMachine` | Sans espace ni accent : il apparaît dans les chemins SMB et dans le Terminal. |
| Location | Volume 1 | Le volume chiffré. |
| Hide this shared folder in "My Network Places" | Coché | Le dossier n'encombre pas la barre latérale du Finder. Time Machine le trouve quand même par Bonjour (8.5), ou par son adresse. |
| Hide sub-folders and files from users without permissions | Coché | Chaque compte ne voit que ce qu'il a le droit de lire. |
| Enable Recycle Bin | **Décoché** | Déconseillé par Synology : Time Machine supprime en permanence des morceaux de ses images, la corbeille se remplirait sans fin. |
| Protect this shared folder by encrypting it | **Décoché** | Déconseillé par Synology pour Time Machine. Le volume est chiffré, et Time Machine chiffre lui-même (8.6). |
| Protect this shared folder with WriteOnce | **Décoché** | Time Machine doit pouvoir supprimer les anciennes sauvegardes. |
| Enable data checksum for advanced data integrity | Coché | Btrfs détecte les données abîmées et le scrubbing les répare depuis l'autre disque. Ne se change plus après la création. |
| Enable file compression | Décoché | Une sauvegarde chiffrée ne se compresse pas : du processeur pour rien. |
| Enable shared folder quota | Coché, 2 To | La somme des quotas des comptes (8.1). |

À l'étape des permissions, donner **Read/Write** au groupe `administrators` si tu veux pouvoir regarder le contenu, et ne rien toucher pour le groupe `users` : laisser toutes ses cases vides. Les comptes Time Machine recevront leurs droits à leur création (8.3).

!! **« No access » l'emporte sur tout :** dans DSM, une case « No access » cochée pour un groupe prime sur le « Read/Write » donné à un compte de ce groupe. Cocher « No access » pour le groupe `users` (dont font partie tous les comptes) bloquerait donc les comptes Time Machine. Pour fermer le dossier aux autres comptes, il suffit de ne leur donner aucun droit.

## 8.3 Créer un compte par Mac

**Control Panel > User & Group > User > Create**, une fois par Mac :

- **Nom :** `tm-` suivi du nom du Mac, par exemple `tm-macbook`. Mot de passe aléatoire et long : le Mac le garde dans son trousseau, personne n'a à le taper au quotidien. Le noter dans ton gestionnaire de mots de passe. Pas d'adresse e-mail.

- **Groupes :** `users` seulement, surtout pas `administrators`.

- **Assign shared folders permissions :** `TimeMachine` en **Read/Write** ; pour tous les autres dossiers, aucune case (ou **No access**, ce qui ne pose pas de problème au niveau d'un compte).

- **Assign user quota :** sur la ligne du volume ou du dossier `TimeMachine`, le quota de ce Mac (8.1).

- **Assign application permissions :** autoriser **SMB** seulement. Refuser DSM, File Station, et tout le reste.

## 8.4 Service SMB

Dans **Control Panel > File Services**, onglet **SMB** : cocher **Enable SMB service**. Puis **Advanced Settings**, et régler :

|= 210.0 130.0 141.9 header
| Option | Valeur | Remarque |
| Maximum SMB protocol | SMB3 | Recommandé par Synology pour Time Machine. |
| Minimum SMB protocol | SMB2 and Large MTU | Coupe SMB1, ancien et peu sûr. Ne pas mettre SMB3 : DSM entend par là SMB 3.1.1 uniquement. |
| Enable Opportunistic Locking | Coché | Recommandé par Synology pour Time Machine. |
| Enable SMB2 lease | Coché | Recommandé par Synology pour Time Machine. |
| Enable SMB durable handles | Coché | Recommandé par Synology : la connexion survit à une courte coupure (Wi-Fi). Désactive le verrouillage de fichiers entre protocoles, sans effet ici. |
| Transport encryption mode | Valeur par défaut | Le chiffrement SMB ralentit les transferts, et la sauvegarde est déjà chiffrée par le Mac. |
| Server signing | Valeur par défaut | Voir la section 8.8 en cas d'échec sous macOS Tahoe. |

Laisser **AFP** désactivé : Apple a retiré la sauvegarde Time Machine par AFP, et Synology recommande SMB seul.

## 8.5 Annonce Bonjour

Toujours dans **Control Panel > File Services**, onglet **Advanced** :

- Cocher **Enable Bonjour service discovery** et **Enable Bonjour Time Machine broadcast via SMB**.

- Cliquer sur **Set Time Machine Folders** et cocher `TimeMachine`.

Le dossier apparaît alors directement dans la liste des disques de sauvegarde proposés par les Mac du réseau local.

## 8.6 Côté Mac

Sur chaque Mac, de préférence **branché en Ethernet et sur secteur** pour la première sauvegarde, qui peut durer plusieurs heures :

- **Réglages Système > Général > Time Machine** (macOS 13 Ventura et suivants), **Ajouter un disque de sauvegarde**.

- Choisir `TimeMachine` sur le NAS (`nas-famille`). S'il n'apparaît pas, le monter d'abord dans le Finder (**Aller > Se connecter au serveur**, `smb://nas-famille.local/TimeMachine`, ou l'adresse IP), puis recommencer.

- Cocher **Chiffrer la sauvegarde** et choisir le mot de passe de chiffrement. Le choix se fait **maintenant** : passer plus tard d'une sauvegarde réseau non chiffrée à une sauvegarde chiffrée oblige à repartir de zéro.

- Saisir le compte de ce Mac (`tm-macbook`) et son mot de passe quand Time Machine les demande. Laisser cocher l'enregistrement dans le trousseau.

- Si macOS propose une **limite d'utilisation du disque**, la laisser sur « Aucune » : le quota du NAS fait déjà ce travail.

!! **Mot de passe de chiffrement Time Machine :** le ranger dans ton gestionnaire de mots de passe et dans celui du propriétaire du Mac. Le Mac le garde dans son trousseau, mais le jour où il faut restaurer sur un Mac neuf, ou après la perte du Mac, ce mot de passe est le seul moyen de lire la sauvegarde.

Pendant la première sauvegarde, empêcher la mise en veille : **Réglages Système > Batterie > Options**, « Empêcher la suspension d'activité automatique sur l'adaptateur secteur lorsque l'écran est éteint » (sur un portable), ou laisser simplement l'écran allumé.

## 8.7 Vérifier

Une fois la première sauvegarde terminée, dans le Terminal du Mac :

```
# Destination, account and kind of the Time Machine target
tmutil destinationinfo
# Time Machine status: Running = 0 when idle
tmutil status
# SMB version and signing of the mounted share (while the backup disk is mounted)
smbutil statshares -a
```

`smbutil` doit montrer `SMB_3` dans la ligne de version pour le partage `TimeMachine`. Puis le seul vrai test : **restaurer un fichier**. Ouvrir un dossier dans le Finder, menu Time Machine (barre des menus) > **Parcourir les sauvegardes Time Machine**, remonter à la sauvegarde du jour, restaurer un fichier, et vérifier qu'il s'ouvre.

Côté NAS, **Control Panel > Shared Folder**, dossier `TimeMachine` : l'occupation doit refléter la taille de la première sauvegarde. Et dans **Resource Monitor > Connections**, la connexion du compte `tm-macbook` doit apparaître en SMB3 pendant une sauvegarde.

## 8.8 Dépannage

### « Un problème est survenu lors de la connexion au serveur »

Souvent un ancien mot de passe resté dans le trousseau. On redéfinit la destination dans le Terminal, avec le compte du Mac (le Terminal doit avoir l'accès complet au disque : **Réglages Système > Confidentialité et sécurité > Accès complet au disque**) :

```
# Replace with this Mac's account and the NAS address
sudo tmutil setdestination -p "smb://tm-macbook@192.168.1.20/TimeMachine"
```

macOS demande d'abord le mot de passe administrateur du Mac (pour `sudo`), puis « Destination password » : celui du compte `tm-macbook`.

### Sauvegardes qui échouent sous macOS Tahoe (26)

Plusieurs versions de macOS Tahoe ont cassé les sauvegardes Time Machine vers des NAS, Synology compris : Apple y a durci la signature SMB, et une version a mal géré les identifiants. Le symptôme est souvent silencieux : plus aucune sauvegarde depuis des jours, sans alerte. Dans l'ordre :

- Mettre à jour macOS et DSM. C'est la vraie correction, à vérifier d'abord.

- Si les sauvegardes échouent toujours, un contournement signalé par plusieurs utilisateurs est de forcer côté Mac la signature SMB et SMB 2 ou 3, dans `/etc/nsmb.conf` (fichier normalement absent) :

```
sudo tee /etc/nsmb.conf <<'EOF'
[default]
signing_required=yes
protocol_vers_map=6
EOF
```

`protocol_vers_map=6` autorise SMB2 et SMB3 (1 = SMB1, 2 = SMB2, 4 = SMB3). Démonter le partage ou redémarrer le Mac pour que le fichier soit pris en compte. Ce n'est pas un réglage officiel d'Apple : le noter, et supprimer le fichier (`sudo rm /etc/nsmb.conf`) si une mise à jour de macOS règle le problème ou si d'autres partages SMB se mettent à poser problème.

### « Time Machine doit créer une nouvelle sauvegarde »

L'image disque est abîmée. Avant d'accepter (ce qui efface tout l'historique), restaurer le snapshot de la veille du dossier `TimeMachine` (section 7.4).

### Plus de place

Time Machine supprime les anciennes sauvegardes quand le quota est atteint, mais s'il manque plus de place que ce qu'une sauvegarde peut libérer, il échoue. Augmenter le quota du compte (Control Panel > User & Group, compte, **Edit > Quota**), et celui du dossier en conséquence.

# 9. Au-delà de ce guide : une vraie sauvegarde

Le NAS protège contre la panne d'un disque (SHR), les fichiers effacés et le rançongiciel (snapshots), et sauvegarde les Mac (Time Machine). Il ne protège pas contre ce qui frappe le NAS entier : vol, incendie, dégât des eaux, surtension, erreur dans DSM. Pour les sauvegardes Time Machine, c'est acceptable : les originaux sont sur les Mac. Pour les fichiers qui ne vivent **que** sur le NAS (photos de famille rangées directement dessus, par exemple), il faut une copie ailleurs.

Le paquet **Hyper Backup** de Synology sait sauvegarder des dossiers partagés, chiffrés et versionnés, vers un disque USB branché sur le NAS (à garder ailleurs entre deux sauvegardes), vers Synology C2 ou un autre stockage en ligne, ou vers une machine distante par rsync, par exemple chez toi à travers Tailscale. Ce sera l'objet d'un guide suivant si besoin.

!todo À faire après l'installation
☐ Clé de récupération du volume rangée dans le gestionnaire de mots de passe et sur une clé USB hors de la maison.
☐ Mot de passe du coffre de clés, mot de passe administrateur et codes de secours de la double authentification rangés.
☐ Mot de passe de chiffrement Time Machine de chaque Mac rangé.
☐ E-mail de test des notifications bien reçu.
☐ Scrubbing trimestriel et tests S.M.A.R.T. planifiés.
☐ Première sauvegarde Time Machine terminée et un fichier restauré avec succès, sur chaque Mac.
☐ Snapshots planifiés sur chaque dossier, et `#snapshot` visible sur les dossiers de données.
☐ Au bout d'un mois : occupation des snapshots du dossier `TimeMachine` vérifiée (Calculate Size).
~ Une fois par an : restaurer un fichier depuis Time Machine et depuis un snapshot, pour vérifier que tout fonctionne encore.
