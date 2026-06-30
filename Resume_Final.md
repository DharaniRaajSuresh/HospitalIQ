\documentclass[letterpaper,11pt]{article}

\usepackage{latexsym}
\usepackage[empty]{fullpage}
\usepackage{titlesec}
\usepackage[usenames,dvipsnames]{color}
\usepackage{enumitem}
\usepackage[hidelinks]{hyperref}
\usepackage{fancyhdr}
\usepackage[english]{babel}
\IfFileExists{glyphtounicode.tex}{\input{glyphtounicode}}{}

\pagestyle{fancy}
\fancyhf{}
\fancyfoot{}
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{0pt}

\addtolength{\oddsidemargin}{-0.6in}
\addtolength{\evensidemargin}{-0.5in}
\addtolength{\textwidth}{1.19in}
\addtolength{\topmargin}{-.75in}
\addtolength{\textheight}{1.7in}

\urlstyle{same}
\raggedbottom
\raggedright
\setlength{\tabcolsep}{0in}

\titleformat{\section}{
  \vspace{-4pt}\scshape\raggedright\large\bfseries
}{}{0em}{}[\color{black}\titlerule \vspace{-5pt}]

\pdfgentounicode=1

\newcommand{\resumeItem}[1]{
  \item\small{{#1 \vspace{-2pt}}}
}

\newcommand{\resumeSubheading}[4]{
  \vspace{-2pt}\item
    \begin{tabular*}{1.0\textwidth}[t]{l@{\extracolsep{\fill}}r}
      \textbf{#1} & \textbf{\small #2} \\
      \textit{\small#3} & \textit{\small #4} \\
    \end{tabular*}\vspace{-6pt}
}

\newcommand{\resumeProjectHeading}[2]{
    \item
    \begin{tabular*}{1.001\textwidth}{l@{\extracolsep{\fill}}r}
      \small#1 & \textbf{\small #2}\\
    \end{tabular*}\vspace{-6pt}
}

\newcommand{\resumeSubItem}[1]{\resumeItem{#1}\vspace{-4pt}}

\renewcommand\labelitemi{$\vcenter{\hbox{\tiny$\bullet$}}$}
\renewcommand\labelitemii{$\vcenter{\hbox{\tiny$\bullet$}}$}

\newcommand{\resumeSubHeadingListStart}{\begin{itemize}[leftmargin=0.0in, label={}]}
\newcommand{\resumeSubHeadingListEnd}{\end{itemize}}
\newcommand{\resumeItemListStart}{\begin{itemize}[itemsep=0pt, topsep=2pt]}
\newcommand{\resumeItemListEnd}{\end{itemize}\vspace{-4pt}}

\begin{document}

%----------HEADING----------
\begin{center}
    {\Huge \scshape Dharani Raaj Suresh} \\ \vspace{2pt}
    \small{B.Tech Computer Science $|$ VIT Chennai} \\ \vspace{2pt}
    Alandur, Chennai, Tamil Nadu 600016 \\ \vspace{2pt}
    \small +91\ 9042503337 \quad
    \href{mailto:dharanisuresh307@gmail.com}{dharanisuresh307@gmail.com} \quad
    \href{https://www.linkedin.com/in/dharani-raaj-s-b55b53323}{linkedin.com/in/dharani-raaj} \quad
    \href{https://github.com/DharaniRaajSuresh}{github.com/DharaniRaajSuresh} \quad
    \vspace{-8pt}
\end{center}

%-----------EDUCATION-----------
\section{Education}
  \resumeSubHeadingListStart
    \resumeSubheading
      {Vellore Institute of Technology (VIT)}{Expected May 2028}
      {Bachelor of Technology in Computer Science $|$ CGPA: 8.35}{Chennai, India}
  \resumeSubHeadingListEnd

%-----------EXPERIENCE-----------
\section{Experience}
  \resumeSubHeadingListStart
    \resumeSubheading
      {HCLTech}{May 2026 -- Jul 2026}
      {Software Engineer Intern}{Chennai, India $|$ \href{https://github.com/DharaniRaajSuresh/HospitalIQ}{\underline{GitHub}}}
      \resumeItemListStart
        \resumeItem{Architected a scalable healthcare AI platform using Spring Boot 3.4 + FastAPI dual-backend microservice architecture --- serving 35 REST APIs across 15 database tables, deploying 9 machine learning models on 1.64M records across 30 Indian states.}
        \resumeItem{Containerized the full stack via Docker Compose (4 services) with CI/CD pipelines using GitHub Actions; built React 19/TypeScript frontend with Agile SDLC delivering 0 TypeScript errors across 14 pages.}
        \resumeItem{Implemented patient microservice with JPA/Hibernate (5 entities), layered architecture, secure JWT (HS256 + bcrypt + httpOnly) for cybersecurity, and 3-tier testing --- 91 tests (62 Python + 29 Java) at 100\% pass rate.}
        \resumeItem{Diagnosed 414\% MAPE due to data leakage in forecast pipeline; replaced Ridge regression with tuned XGBoost using chronological train/test splits, reducing error 42$\times$ to 9.8\%.}
        \resumeItem{Optimized frontend performance with stale-while-revalidate caching (5-min TTL) and Vite code-splitting into 32 chunks (5 vendor groups), reducing Lighthouse load times by $\sim$60\%.}
      \resumeItemListEnd
  \resumeSubHeadingListEnd
\vspace{-8pt}

%-----------PROJECTS-----------
\section{Projects}
    \vspace{-5pt}
    \resumeSubHeadingListStart
      \resumeProjectHeading
          {\textbf{AI Scam Shield} $|$ \emph{React, FastAPI, WebSockets, \mbox{Agora RTC/STT}, NLP}}{\href{https://github.com/DharaniRaajSuresh/realtimeScamfinal}{GitHub} $|$ Jan 2026 -- Feb 2026}
          \resumeItemListStart
            \resumeItem{Engineered a low-latency real-time scam detection system using deep learning STT to transcribe and analyze live multilingual (English/Tamil) calls with sub-second latency --- classified 5 scam types with real-time risk scoring.}
            \resumeItem{Built async FastAPI + WebSocket backend handling 500+ concurrent connections with NLP engine for real-time scam classification and risk scoring.}
            \resumeItem{Developed geospatial dashboards for visualizing scam hotspots and alert trends across regions in real time.}
          \resumeItemListEnd
          \vspace{-10pt}
      \resumeProjectHeading
          {\textbf{ATHER} $|$ \emph{React, TypeScript, Node.js, CesiumJS, Gemini AI, Tailwind CSS}}{\href{https://github.com/DharaniRaajSuresh/GreenRouting}{GitHub} $|$ Feb 2026 -- Mar 2026}
          \resumeItemListStart
            \resumeItem{Developed an urban CO\textsubscript{2} digital twin platform fusing real-time data from 5+ APIs (Open-Meteo, TomTom, Mapbox, OSM) with Google Gemini GenAI for predictive AQI forecasting and traffic analytics across urban zones.}
            \resumeItem{Engineered interactive 3D city visualizations using CesiumJS with custom particle systems and physics-based CO\textsubscript{2} reduction modeling for multiple urban environments.}
            \resumeItem{Constructed Node.js/Express backend with multi-layer caching, intelligent API batching, and structured Gemini AI output parsing with fallback systems.}
          \resumeItemListEnd
          \vspace{-10pt}
      \resumeProjectHeading
          {\textbf{Healthcare Management System} $|$ \emph{Next.js, TypeScript, PostgreSQL, WebSockets}}{Mar 2026 -- Apr 2026}
          \resumeItemListStart
            \resumeItem{Architected a full-stack platform with role-based dashboards (patient/doctor/admin), JWT auth, and RBAC --- 15+ REST APIs for appointments, medical records, and product orders on PostgreSQL.}
            \resumeItem{Implemented real-time chat, data sync, and step-count tracking via WebSockets and browser sensor APIs.}
          \resumeItemListEnd
    \resumeSubHeadingListEnd
\vspace{-8pt}

%-----------SKILLS-----------
\section{Technical Skills}
\begin{itemize}[leftmargin=0.15in, label={}]
    \small{\item{
      \textbf{Languages}{: Java, Python, C++, JavaScript, TypeScript, SQL} \\[2pt]
      \textbf{Frameworks}{: Spring Boot, Spring Security, Spring Data JPA, JPA/Hibernate, JUnit/Mockito, React, FastAPI, Node.js, Next.js} \\[2pt]
      \textbf{Tools \& Technologies}{: XGBoost, scikit-learn, PostgreSQL, Docker, REST APIs, WebSockets, Git, GitHub Actions, Maven, Microservices} \\[2pt]
      \textbf{Competitive Programming}{: LeetCode -- \href{https://leetcode.com/u/DRJ18/}{DRJ18} (update count before applying)} \\[2pt]
      \textbf{Relevant Coursework}{: Data Structures \& Algorithms, Operating Systems, Database Management Systems} \\[2pt]
      \textbf{Extracurricular}{: OSPC -- VIT Chennai (Member)} \\
    }}
\end{itemize}
\vspace{-8pt}

\end{document}