# Document de Conception : Re:Search

## The Interactive Library of Alexandria

## 1. Vision du Produit

Re:Search n'est pas seulement un moteur de recherche ou un éditeur de texte. C'est une Base de Connaissance Augmentée. L'objectif est de permettre à l'utilisateur de construire sa propre "Bibliothèque d'Alexandrie" personnelle, curée manuellement mais gérée et étendue par des agents IA.
La philosophie centrale est la persistance et l'interconnexion : contrairement à une discussion ChatGPT éphémère, ici chaque recherche contribue à une mémoire à long terme structurée.

## 2. L'Interface Hybride (UI/UX)

L'interface repose sur une dualité entre la Vue Macro (Exploration) et la Vue Micro (Création).

### A. La Vue "Projet" : Le Crazy Board (Infinite Canvas)

C'est la vue d'ensemble d'un projet. Elle reprend l'esthétique du tableau d'enquêteur.

- Fonction : Visualiser les connexions entre les documents, les sources web, et les notes.
- Interaction : Zoom sémantique. L'utilisateur peut glisser-déposer des sources, dessiner des liens (fils rouges) entre des concepts, et regrouper des "artefacts" visuellement.
- Usage : C'est ici que l'on structure la pensée avant d'écrire.

### B. La Vue "Artefact" : L'Éditeur (Style VS Code)

Lorsque l'utilisateur clique sur un élément du Canvas pour "travailler", il bascule (ou ouvre un panneau) dans une vue éditeur puissante.

- Inspiration : VS Code / Obsidian.
- Fonctionnalités :
    - Édition de texte riche / Code / Markdown. Et toggle preview mode for markdown content
    - Wiki-linking : Possibilité de souligner/lier des mots-clés qui renvoient vers d'autres documents ou projets (système hypertexte interne).
    - Panneau Latéral IA : Un chat contextuel ("Copilote") dédié au fichier ouvert. Il peut répondre à des questions sur le fichier, le résumer, ou le modifier directement.

## 1. Les Agents IA & La "Deep Memory"

Le cœur du système est l'intelligence artificielle qui agit comme bibliothécaire et enquêteur.

### Le Chatbot Omniscient (Global)

- Un chat général qui a accès à toute la base de données de l'utilisateur (Deep Memory Management).
- Il peut retrouver une info croisée entre deux projets distincts (ex: "Quel est le lien entre mes notes sur l'architecture romaine et ce projet de SF ?").

### Le "Researcher Agent" (Mode Recherche)

C'est un agent autonome capable de planifier.

- Input : L'utilisateur donne un objectif (ex: "Fais un état de l'art sur les batteries solides").
- Planification : L'agent établit un plan de recherche.
- Exploration : Il navigue sur le web, lit les sources, écarte les publicités/bruit.
- Indexation : Il sauvegarde les sources pertinentes dans la base de données.
- Synthèse : Il compile les résultats dans un rapport dédié (qui devient un nouvel "Artefact" sur le Canvas).

## 1. Scénario d'Utilisation (User Journey)

Imaginez un utilisateur écrivant un roman policier historique.

- Lancement (Chat Général) :
    - User: "Je veux commencer un projet sur les crimes dans le Paris du 19ème siècle."
    - App: Crée un nouveau projet "Paris 19ème" et ouvre un Canvas vide.
- Recherche (Researcher Agent) :
    - User (sur le Canvas): "Trouve-moi des cartes de Paris en 1850 et des articles sur la Vidocq."
    - Agent: Scanne le web, télécharge 5 cartes et 3 articles PDF. Il les dispose automatiquement sur le Canvas sous forme de cartes reliées.
- Création (Vue Artefact) :
    - L'utilisateur ouvre un fichier texte "Chapitre 1".
    - Il écrit. Il a un doute. Il demande au Panneau Latéral : "Est-ce que la rue de la Paix existait à cette date ?".
    - L'IA vérifie dans les cartes téléchargées à l'étape 2 et répond.
- Connexion (Wiki-linking) :
    - L'utilisateur écrit le mot "Vidocq". Il le transforme en lien. S'il clique dessus, le système ouvre la fiche "Vidocq" que l'IA avait préparée plus tôt.

## 1. Architecture Technique (Suggestion)

Pour réaliser cette vision "VS Code meets Miro", voici une stack technique cohérente :

- Frontend : Electron ou Tauri (pour avoir une app bureau performante type VS Code).
- Canvas Engine : React Flow ou Tldraw (pour le côté "Crazy Board").
- Éditeur Texte : Monaco Editor (le moteur de VS Code) ou ProseMirror (plus flexible pour le riche texte).
- Backend / AI :
    - Vector Database (ex: Pinecone ou Weaviate) : C'est crucial pour la "Deep Memory". Cela permet à l'IA de faire des recherches sémantiques dans vos documents locaux.
    - Orchestrateur (LangChain) : Pour gérer le "Researcher Agent" qui navigue sur le web.