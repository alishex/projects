(function () {
  "use strict";

  var STRINGS = {
    "meta.title": {
      en: "Narzullo Muhammad Ali Narzullayev — Cyber Security Engineer (OSCP)",
      uz: "Narzullo Muhammad Ali Narzullayev — Kiberxavfsizlik muhandisi (OSCP)",
      ru: "Narzullo Muhammad Ali Narzullayev — Инженер по кибербезопасности (OSCP)"
    },
    "meta.description": {
      en: "Narzullo Muhammad Ali Narzullayev — OSCP-certified Cyber Security Engineer, Penetration Tester and IT Systems Engineer. Offensive security, Active Directory, network security, and infrastructure.",
      uz: "Narzullo Muhammad Ali Narzullayev — OSCP sertifikatiga ega kiberxavfsizlik muhandisi, penetration tester va IT tizimlar muhandisi. Hujumkor xavfsizlik, Active Directory, tarmoq xavfsizligi va infratuzilma.",
      ru: "Narzullo Muhammad Ali Narzullayev — сертифицированный OSCP инженер по кибербезопасности, пентестер и инженер IT-систем. Наступательная безопасность, Active Directory, сетевая безопасность и инфраструктура."
    },
    "meta.ogDescription": {
      en: "Think Like an Attacker. Protect Like an Engineer.",
      uz: "Hujumchidek fikrla. Muhandisdek himoya qil.",
      ru: "Думай как атакующий. Защищай как инженер."
    },

    "nav.about": { en: "about", uz: "haqida", ru: "обо мне" },
    "nav.experience": { en: "experience", uz: "tajriba", ru: "опыт" },
    "nav.certs": { en: "certs", uz: "sertifikatlar", ru: "сертификаты" },
    "nav.skills": { en: "skills", uz: "ko'nikmalar", ru: "навыки" },
    "nav.contact": { en: "contact", uz: "aloqa", ru: "контакты" },

    "hero.kicker": {
      en: "available for offensive security engagements",
      uz: "hujumkor xavfsizlik loyihalari uchun ochiqman",
      ru: "открыт для проектов по наступательной безопасности"
    },
    "hero.role": { en: "Cyber Security Engineer", uz: "Kiberxavfsizlik muhandisi", ru: "Инженер по кибербезопасности" },
    "hero.tagline": {
      en: "Penetration Tester • Security Researcher • IT Systems Engineer",
      uz: "Penetration Tester • Xavfsizlik tadqiqotchisi • IT tizimlar muhandisi",
      ru: "Пентестер • Исследователь безопасности • Инженер IT-систем"
    },
    "hero.motto": {
      en: "“Think Like an Attacker. Protect Like an Engineer.”",
      uz: "“Hujumchidek fikrla. Muhandisdek himoya qil.”",
      ru: "“Думай как атакующий. Защищай как инженер.”"
    },
    "hero.cta1": { en: "Contact on Telegram", uz: "Telegram orqali bog'lanish", ru: "Связаться в Telegram" },
    "hero.cta2": { en: "View OSCP Certification", uz: "OSCP sertifikatini ko'rish", ru: "Посмотреть сертификат OSCP" },

    "alt.profileHero": {
      en: "Portrait of Narzullo Muhammad Ali",
      uz: "Narzullo Muhammad Alining portreti",
      ru: "Портрет — Narzullo Muhammad Ali"
    },
    "alt.profileContact": {
      en: "Narzullo Muhammad Ali",
      uz: "Narzullo Muhammad Ali",
      ru: "Narzullo Muhammad Ali"
    },

    "aria.oscpFull": {
      en: "Open full-resolution OSCP certificate in a new tab",
      uz: "OSCP sertifikatini to'liq o'lchamda yangi oynada ochish",
      ru: "Открыть сертификат OSCP в полном разрешении в новой вкладке"
    },
    "aria.satFull": {
      en: "Open full-resolution SAT score report in a new tab",
      uz: "SAT ball hisobotini to'liq o'lchamda yangi oynada ochish",
      ru: "Открыть отчёт о результатах SAT в полном разрешении в новой вкладке"
    },
    "aria.grantFull": {
      en: "Open full-resolution PDP University grant certificate in a new tab",
      uz: "PDP University grant sertifikatini to'liq o'lchamda yangi oynada ochish",
      ru: "Открыть сертификат гранта PDP University в полном разрешении в новой вкладке"
    },
    "aria.dtmFull": {
      en: "Open full-resolution national admission test results in a new tab",
      uz: "Milliy qabul imtihoni natijalarini to'liq o'lchamda yangi oynada ochish",
      ru: "Открыть результаты национального вступительного теста в полном разрешении в новой вкладке"
    },
    "alt.oscpCert": {
      en: "Offensive Security Certified Professional certificate awarded to Narzullo Muhammad Ali Nazirjonovich, issued July 2, 2026",
      uz: "Narzullo Muhammad Ali Nazirjonovichga 2026-yil 2-iyulda berilgan Offensive Security Certified Professional sertifikati",
      ru: "Сертификат Offensive Security Certified Professional, выданный Narzullo Muhammad Ali Nazirjonovich 2 июля 2026 года"
    },
    "alt.satCert": {
      en: "SAT Score Report — Total Score 1270 out of 1600",
      uz: "SAT ball hisoboti — Umumiy ball 1270 / 1600",
      ru: "Отчёт о результатах SAT — общий балл 1270 из 1600"
    },
    "alt.grantCert": {
      en: "PDP University Grant certificate awarded to Narzullo Muhammad Ali — 12,000,000 so'm",
      uz: "Narzullo Muhammad Aliga berilgan PDP University Grant sertifikati — 12 000 000 so'm",
      ru: "Сертификат гранта PDP University, выданный Narzullo Muhammad Ali — 12 000 000 сум"
    },
    "alt.dtmCert": {
      en: "National university entrance examination results — recommended for admission to Tashkent University of Information Technologies (TUIT)",
      uz: "Milliy oliy o'quv yurtiga kirish imtihoni natijalari — Tashkent University of Information Technologies (TUIT)ga tavsiya etilgan",
      ru: "Результаты национального вступительного экзамена в вуз — рекомендация к зачислению в Tashkent University of Information Technologies (TUIT)"
    },

    "eyebrow.about": { en: "about", uz: "haqida", ru: "обо мне" },
    "eyebrow.summary": { en: "professional summary", uz: "professional xulosa", ru: "профессиональное резюме" },
    "eyebrow.experience": { en: "experience", uz: "tajriba", ru: "опыт" },
    "eyebrow.certifications": { en: "certifications", uz: "sertifikatlar", ru: "сертификаты" },
    "eyebrow.skills": { en: "skills", uz: "ko'nikmalar", ru: "навыки" },
    "eyebrow.timeline": { en: "my journey", uz: "mening yo'lim", ru: "мой путь" },
    "eyebrow.education": { en: "education", uz: "ta'lim", ru: "образование" },
    "eyebrow.values": { en: "core values", uz: "asosiy qadriyatlar", ru: "основные ценности" },
    "eyebrow.mission": { en: "mission", uz: "missiya", ru: "миссия" },
    "eyebrow.vision": { en: "vision", uz: "vizyon", ru: "видение" },
    "eyebrow.philosophy": { en: "philosophy", uz: "falsafa", ru: "философия" },
    "eyebrow.contact": { en: "contact", uz: "aloqa", ru: "контакты" },

    "about.lead": {
      en: "Cybersecurity is more than a profession to me—it is a mindset driven by curiosity, discipline, and continuous learning. I enjoy understanding how systems work, discovering how they can fail, and helping organizations build stronger defenses against modern cyber threats.",
      uz: "Kiberxavfsizlik men uchun shunchaki kasb emas — bu qiziqish, intizom va uzluksiz o'rganishga asoslangan turmush tarzi. Men tizimlarning qanday ishlashini, ular qanday nosozliklarga uchrashi mumkinligini tushunishni va tashkilotlarga zamonaviy kiber tahdidlarga qarshi kuchliroq himoya qurishda yordam berishni yoqtiraman.",
      ru: "Кибербезопасность для меня — больше, чем профессия. Это образ мышления, основанный на любопытстве, дисциплине и непрерывном обучении. Мне нравится понимать, как устроены системы, находить способы их отказа и помогать организациям выстраивать более надёжную защиту от современных киберугроз."
    },
    "about.p2": {
      en: "I specialize in Offensive Security, Penetration Testing, Web Application Security, Active Directory Security, Linux systems, and Network Security. Every assessment I perform is approached from an attacker's perspective, allowing me to identify vulnerabilities before they can be exploited by malicious actors.",
      uz: "Men Offensive Security, Penetration Testing, veb-ilovalar xavfsizligi, Active Directory xavfsizligi, Linux tizimlari va tarmoq xavfsizligi bo'yicha ixtisoslashganman. Har bir baholashga hujumchi nuqtai nazaridan yondashaman — bu zaifliklarni yovuz niyatli shaxslar ulardan foydalanishidan oldin aniqlash imkonini beradi.",
      ru: "Я специализируюсь на Offensive Security, Penetration Testing, безопасности веб-приложений, безопасности Active Directory, системах Linux и сетевой безопасности. К каждому анализу я подхожу с точки зрения атакующего — это позволяет находить уязвимости раньше, чем ими воспользуются злоумышленники."
    },
    "about.p3": {
      en: "I currently work as an <strong style=\"color:var(--text)\">IT Systems Engineer</strong>, where I contribute to maintaining secure and reliable IT infrastructure while continuously expanding my expertise in offensive security. My professional journey reflects a balance between system administration, infrastructure management, and practical penetration testing.",
      uz: "Hozirda men <strong style=\"color:var(--text)\">IT tizimlar muhandisi</strong> lavozimida ishlayman — bu yerda xavfsiz va ishonchli IT infratuzilmani saqlashga hissa qo'shaman, shu bilan birga hujumkor xavfsizlik sohasidagi bilimlarimni doimiy kengaytiraman. Kasbiy yo'lim tizim administratsiyasi, infratuzilmani boshqarish va amaliy penetration testing o'rtasidagi muvozanatni aks ettiradi.",
      ru: "В настоящее время я работаю <strong style=\"color:var(--text)\">инженером IT-систем</strong> — обеспечиваю безопасность и надёжность IT-инфраструктуры, одновременно постоянно расширяя экспертизу в сфере наступательной безопасности. Мой профессиональный путь отражает баланс между системным администрированием, управлением инфраструктурой и практическим penetration testing."
    },
    "about.p4": {
      en: "One of the most significant milestones in my career has been earning the <strong style=\"color:var(--text)\">Offensive Security Certified Professional (OSCP)</strong> certification—one of the most respected hands-on penetration testing certifications in the industry. It demonstrates my ability to think critically, solve complex security challenges, and perform real-world penetration testing under pressure.",
      uz: "Karyeramdagi eng muhim yutuqlardan biri — <strong style=\"color:var(--text)\">Offensive Security Certified Professional (OSCP)</strong> sertifikatiga ega bo'lishim edi. Bu sohadagi eng nufuzli amaliy penetration testing sertifikatlaridan biri bo'lib, tanqidiy fikrlash, murakkab xavfsizlik muammolarini yechish va bosim ostida real hayotiy penetration testing o'tkazish qobiliyatimni namoyish etadi.",
      ru: "Одним из важнейших этапов моей карьеры стало получение сертификата <strong style=\"color:var(--text)\">Offensive Security Certified Professional (OSCP)</strong> — одного из самых уважаемых практических сертификатов по penetration testing в отрасли. Он подтверждает способность мыслить критически, решать сложные задачи в сфере безопасности и проводить реальное тестирование на проникновение под давлением."
    },
    "about.p5": {
      en: "Technology evolves every day, and so do I. I believe that continuous learning is the foundation of excellence. Every project, challenge, and vulnerability is another opportunity to grow, improve, and make the digital world a safer place.",
      uz: "Texnologiya har kuni rivojlanadi, men ham shunday. Uzluksiz o'rganish — mukammallikning poydevori, deb ishonaman. Har bir loyiha, har bir muammo va har bir zaiflik — o'sish, rivojlanish va raqamli dunyoni xavfsizroq qilish uchun yana bir imkoniyat.",
      ru: "Технологии развиваются каждый день — и я вместе с ними. Я убеждён, что непрерывное обучение — основа мастерства. Каждый проект, каждая задача и каждая уязвимость — это ещё одна возможность расти, совершенствоваться и делать цифровой мир безопаснее."
    },
    "about.pull": {
      en: "“Every assessment is approached from an attacker's perspective—identifying vulnerabilities before malicious actors do.”",
      uz: "“Har bir baholash hujumchi nuqtai nazaridan amalga oshiriladi — zaifliklarni yovuz niyatli shaxslar ulardan foydalanishidan oldin aniqlash.”",
      ru: "“К каждому анализу я подхожу с точки зрения атакующего — нахожу уязвимости раньше, чем это сделают злоумышленники.”"
    },
    "stat.years": {
      en: "years investing in myself, non-stop",
      uz: "o'zimga to'xtovsiz sarmoya kiritayotgan yillar",
      ru: "лет непрерывных инвестиций в себя"
    },
    "stat.oscp": {
      en: "Offensive Security Certified Professional",
      uz: "Offensive Security Certified Professional",
      ru: "Offensive Security Certified Professional"
    },
    "stat.sat": { en: "SAT score", uz: "SAT balli", ru: "балл SAT" },
    "stat.programming": {
      en: "started programming journey",
      uz: "dasturlash yo'lini boshlagan yil",
      ru: "начал путь в программировании"
    },

    "summary.lead": {
      en: "Cyber Security Engineer with a strong academic foundation and practical experience in Offensive Security, enterprise IT infrastructure, and Information Security.",
      uz: "Offensive Security, korporativ IT infratuzilmasi va Axborot xavfsizligi bo'yicha mustahkam akademik bilim va amaliy tajribaga ega kiberxavfsizlik muhandisi.",
      ru: "Инженер по кибербезопасности с прочной академической базой и практическим опытом в Offensive Security, корпоративной IT-инфраструктуре и информационной безопасности."
    },
    "summary.p": {
      en: "Currently working as an IT Systems Engineer while pursuing a Bachelor's degree in Information Security at TUIT. OSCP-certified with a passion for penetration testing, security research, and continuous professional development.",
      uz: "Hozirda TUITda Axborot xavfsizligi yo'nalishi bo'yicha bakalavriatni davom ettirgan holda IT tizimlar muhandisi sifatida ishlayman. OSCP sertifikatiga ega bo'lib, penetration testing, xavfsizlik tadqiqotlari va uzluksiz kasbiy rivojlanishga ishtiyoqmandman.",
      ru: "В настоящее время работаю инженером IT-систем, параллельно обучаясь на бакалавриате по информационной безопасности в TUIT. Сертифицирован по OSCP, увлечён penetration testing, исследованиями в области безопасности и непрерывным профессиональным развитием."
    },

    "exp.role": { en: "IT Systems Engineer", uz: "IT tizimlar muhandisi", ru: "Инженер IT-систем" },
    "exp.org": { en: "Infrastructure & Security", uz: "Infratuzilma va Xavfsizlik", ru: "Инфраструктура и безопасность" },
    "exp.desc": {
      en: "Responsible for maintaining, supporting, and securing enterprise IT infrastructure while ensuring system reliability, performance, and security.",
      uz: "Korporativ IT infratuzilmasining ishonchliligi, unumdorligi va xavfsizligini ta'minlagan holda uni saqlash, qo'llab-quvvatlash va himoya qilish uchun javobgarman.",
      ru: "Отвечаю за обслуживание, поддержку и защиту корпоративной IT-инфраструктуры, обеспечивая надёжность, производительность и безопасность систем."
    },
    "exp.resp1": { en: "Managing Windows and Linux systems", uz: "Windows va Linux tizimlarini boshqarish", ru: "Администрирование систем Windows и Linux" },
    "exp.resp2": { en: "Network administration and troubleshooting", uz: "Tarmoq administratsiyasi va nosozliklarni bartaraf etish", ru: "Администрирование сети и устранение неполадок" },
    "exp.resp3": { en: "Infrastructure monitoring and maintenance", uz: "Infratuzilmani monitoring qilish va texnik xizmat ko'rsatish", ru: "Мониторинг и обслуживание инфраструктуры" },
    "exp.resp4": { en: "User and system administration", uz: "Foydalanuvchi va tizim administratsiyasi", ru: "Администрирование пользователей и систем" },
    "exp.resp5": { en: "Security hardening", uz: "Xavfsizlikni mustahkamlash", ru: "Усиление защищённости" },
    "exp.resp6": { en: "Incident investigation and response", uz: "Hodisalarni tekshirish va ularga javob berish", ru: "Расследование инцидентов и реагирование" },
    "exp.resp7": { en: "Vulnerability assessment", uz: "Zaifliklarni baholash", ru: "Оценка уязвимостей" },
    "exp.resp8": { en: "Documentation and technical support", uz: "Hujjatlashtirish va texnik yordam", ru: "Документирование и техническая поддержка" },

    "cert.viewFull": { en: "view full resolution ↗", uz: "to'liq o'lchamda ko'rish ↗", ru: "смотреть в полном размере ↗" },

    "cert.oscp.issuer": {
      en: "Offensive Security Certified Professional — Offensive Security",
      uz: "Offensive Security Certified Professional — Offensive Security",
      ru: "Offensive Security Certified Professional — Offensive Security"
    },
    "cert.oscp.date": { en: "Issued July 2, 2026", uz: "2026-yil 2-iyulda berilgan", ru: "Выдан 2 июля 2026 года" },
    "cert.oscp.desc": {
      en: "Advanced hands-on penetration testing certification, earned through a fully practical exam.",
      uz: "To'liq amaliy imtihon orqali qo'lga kiritilgan ilg'or amaliy penetration testing sertifikati.",
      ru: "Продвинутый практический сертификат по penetration testing, полученный через полностью практический экзамен."
    },
    "cert.oscp.check1": { en: "Practical Exam", uz: "Amaliy imtihon", ru: "Практический экзамен" },
    "cert.oscp.check2": { en: "Exploitation", uz: "Ekspluatatsiya", ru: "Эксплуатация" },
    "cert.oscp.check3": { en: "Privilege Escalation", uz: "Imtiyozlarni oshirish (Privilege Escalation)", ru: "Повышение привилегий (Privilege Escalation)" },
    "cert.oscp.check4": { en: "Active Directory", uz: "Active Directory", ru: "Active Directory" },
    "cert.oscp.check5": { en: "Report Writing", uz: "Hisobot yozish", ru: "Написание отчётов" },

    "cert.sat.issuer": { en: "SAT Score Report — College Board", uz: "SAT ball hisoboti — College Board", ru: "Отчёт о результатах SAT — College Board" },
    "cert.sat.date": { en: "Issued 2023", uz: "2023-yilda berilgan", ru: "Выдан в 2023 году" },
    "cert.sat.desc": {
      en: "Additional academic achievement, alongside OSCP — strong analytical thinking, logical reasoning, and problem-solving ability.",
      uz: "OSCP bilan bir qatorda qo'lga kiritilgan qo'shimcha akademik yutuq — kuchli analitik fikrlash, mantiqiy mulohaza va muammolarni yechish qobiliyatini tasdiqlaydi.",
      ru: "Дополнительное академическое достижение наряду с OSCP — подтверждает сильное аналитическое мышление, логическое рассуждение и способность решать задачи."
    },
    "cert.sat.check1": { en: "Total Score — 1270 / 1600", uz: "Umumiy ball — 1270 / 1600", ru: "Общий балл — 1270 / 1600" },
    "cert.sat.check2": { en: "Evidence-Based Reading & Writing — 530/800", uz: "Dalilga asoslangan o'qish va yozish — 530/800", ru: "Чтение и письмо на основе доказательств — 530/800" },
    "cert.sat.check3": { en: "Math — 740/800", uz: "Matematika — 740/800", ru: "Математика — 740/800" },
    "cert.sat.check4": {
      en: "93rd percentile (Nationally Representative Sample)",
      uz: "93-protsentil (Nationally Representative Sample)",
      ru: "93-й процентиль (Nationally Representative Sample)"
    },

    "cert.grant.issuer": {
      en: "Republic Mathematics Olympiad, Selection Stage — PDP University",
      uz: "Respublika matematika olimpiadasi, Saralash bosqichi — PDP University",
      ru: "Республиканская олимпиада по математике, отборочный этап — PDP University"
    },
    "cert.grant.date": { en: "Issued February 7, 2023", uz: "2023-yil 7-fevralda berilgan", ru: "Выдан 7 февраля 2023 года" },
    "cert.grant.desc": {
      en: "Awarded a full merit grant for a top result in the Republic Mathematics Olympiad selection stage, covering winter admission to PDP University's Foundation Programme.",
      uz: "Respublika matematika olimpiadasining saralash bosqichida yuqori natija ko'rsatganim uchun PDP University Foundation Programme'siga qishki qabul uchun to'liq grant bilan taqdirlandim.",
      ru: "Награждён полным грантом за высокий результат на отборочном этапе Республиканской олимпиады по математике — грант покрыл зимнее поступление на Foundation Programme в PDP University."
    },
    "cert.grant.check1": {
      en: "Republic Mathematics Olympiad — Selection Stage",
      uz: "Respublika matematika olimpiadasi — Saralash bosqichi",
      ru: "Республиканская олимпиада по математике — отборочный этап"
    },
    "cert.grant.check2": { en: "12,000,000 so'm merit grant", uz: "12 000 000 so'mlik grant", ru: "Грант — 12 000 000 сум" },
    "cert.grant.check3": { en: "Winter admission, Foundation Programme", uz: "Qishki qabul, Foundation Programme", ru: "Зимнее поступление, Foundation Programme" },

    "cert.dtm.issuer": {
      en: "National University Entrance Examination — Agency for Assessment of Knowledge and Skills",
      uz: "Milliy oliy o'quv yurtiga kirish imtihoni — Bilim va malakalarni baholash agentligi",
      ru: "Национальный вступительный экзамен в вуз — Агентство по оценке знаний и навыков"
    },
    "cert.dtm.date": { en: "Issued July 19, 2024", uz: "2024-yil 19-iyulda berilgan", ru: "Выдан 19 июля 2024 года" },
    "cert.dtm.desc": {
      en: "State admission test results, recommended for enrollment at Tashkent University of Information Technologies (TUIT).",
      uz: "Davlat qabul imtihoni natijalari — Tashkent University of Information Technologies (TUIT)ga talabalikka tavsiya etildim.",
      ru: "Результаты государственного вступительного теста — рекомендован к зачислению в Tashkent University of Information Technologies (TUIT)."
    },
    "cert.dtm.check1": { en: "Overall score — 183.60", uz: "Umumiy ball — 183.60", ru: "Общий балл — 183.60" },
    "cert.dtm.check2": { en: "Mandatory subjects", uz: "Majburiy fanlar", ru: "Обязательные предметы" },
    "cert.dtm.check3": { en: "Mathematics", uz: "Matematika", ru: "Математика" },
    "cert.dtm.check4": { en: "Physics", uz: "Fizika", ru: "Физика" },

    "skills.group1": { en: "Offensive Security", uz: "Hujumkor xavfsizlik", ru: "Наступательная безопасность" },
    "skills.group2": { en: "Programming", uz: "Dasturlash", ru: "Программирование" },
    "skills.group3": { en: "Operating Systems", uz: "Operatsion tizimlar", ru: "Операционные системы" },
    "skills.group4": { en: "Networking", uz: "Tarmoq", ru: "Сети" },
    "skills.group5": { en: "Tools", uz: "Vositalar", ru: "Инструменты" },

    "journey.intro": {
      en: "From replacing high school with university-level cybersecurity education at PDP University, to earning the OSCP certification and pursuing a Bachelor's degree in Information Security at TUIT, my journey has been driven by one principle: never stop learning. Every milestone represents not only an achievement but also a commitment to becoming a better security professional.",
      uz: "Maktabni PDP University'dagi universitet darajasidagi kiberxavfsizlik ta'limiga almashtirishdan tortib, OSCP sertifikatini qo'lga kiritish va TUITda Axborot xavfsizligi yo'nalishi bo'yicha bakalavriatni davom ettirishgacha — mening yo'lim bitta tamoyilga asoslangan: hech qachon o'rganishni to'xtatmaslik. Har bir bosqich nafaqat yutuq, balki yaxshiroq xavfsizlik mutaxassisi bo'lishga bo'lgan sodiqlikni ham anglatadi.",
      ru: "От замены школы университетским образованием в сфере кибербезопасности в PDP University до получения сертификата OSCP и обучения на бакалавриате по информационной безопасности в TUIT — мой путь основан на одном принципе: никогда не переставать учиться. Каждый этап — это не только достижение, но и приверженность становлению более сильным специалистом по безопасности."
    },

    "tl.2022.title": { en: "PDP University", uz: "PDP University", ru: "PDP University" },
    "tl.2022.desc": {
      en: "Started the Foundation Programme in Cyber Security, replacing the traditional 10th and 11th grades with university-level education. During this period, I built a strong foundation in programming, networking, Linux, cybersecurity fundamentals, and computer science.",
      uz: "An'anaviy 10- va 11-sinflar o'rniga universitet darajasidagi ta'lim beruvchi Kiberxavfsizlik yo'nalishidagi Foundation Programme'ni boshladim. Shu davrda dasturlash, tarmoqlar, Linux, kiberxavfsizlik asoslari va kompyuter fanlari bo'yicha mustahkam bilim poydevorini yaratdim.",
      ru: "Начал Foundation Programme по кибербезопасности — эта программа заменила традиционные 10 и 11 классы университетским образованием. За это время я заложил прочную основу в программировании, сетях, Linux, основах кибербезопасности и информатике."
    },

    "tl.2023.title": { en: "SAT — 1270", uz: "SAT — 1270", ru: "SAT — 1270" },
    "tl.2023.desc": {
      en: "Successfully achieved a 1270 SAT score, demonstrating strong analytical thinking, mathematical reasoning, and problem-solving skills.",
      uz: "1270 ball SAT natijasiga muvaffaqiyatli erishdim — bu kuchli analitik fikrlash, matematik mulohaza va muammolarni yechish qobiliyatimni namoyish etadi.",
      ru: "Успешно набрал 1270 баллов по SAT, что демонстрирует сильное аналитическое мышление, математическое рассуждение и способность решать задачи."
    },

    "tl.2024.diploma.title": { en: "Foundation Diploma", uz: "Foundation Diploma", ru: "Foundation Diploma" },
    "tl.2024.diploma.desc": {
      en: "Successfully completed the two-year Foundation Programme in Cyber Security at PDP University and earned my Foundation Diploma.",
      uz: "PDP University'dagi ikki yillik Kiberxavfsizlik yo'nalishidagi Foundation Programme'ni muvaffaqiyatli tamomlab, Foundation Diploma'ga ega bo'ldim.",
      ru: "Успешно завершил двухлетнюю Foundation Programme по кибербезопасности в PDP University и получил Foundation Diploma."
    },
    "tl.2024.tuit.title": {
      en: "Tashkent University of Information Technologies (TUIT)",
      uz: "Tashkent University of Information Technologies (TUIT)",
      ru: "Tashkent University of Information Technologies (TUIT)"
    },
    "tl.2024.tuit.desc": {
      en: "Admitted to the Bachelor's programme in Information Security, where I continue to deepen my expertise in cybersecurity, secure systems, cryptography, network defense, and modern information protection technologies.",
      uz: "Axborot xavfsizligi yo'nalishi bo'yicha bakalavriatga qabul qilindim — bu yerda kiberxavfsizlik, xavfsiz tizimlar, kriptografiya, tarmoqni himoya qilish va zamonaviy axborotni himoya qilish texnologiyalari bo'yicha bilimlarimni chuqurlashtirishda davom etmoqdaman.",
      ru: "Поступил на бакалавриат по информационной безопасности, где продолжаю углублять экспертизу в кибербезопасности, защищённых системах, криптографии, сетевой защите и современных технологиях защиты информации."
    },

    "tl.2026.title": {
      en: "Offensive Security Certified Professional (OSCP)",
      uz: "Offensive Security Certified Professional (OSCP)",
      ru: "Offensive Security Certified Professional (OSCP)"
    },
    "tl.2026.desc": {
      en: "Earned the internationally recognized OSCP certification on July 2, 2026, demonstrating practical expertise in real-world penetration testing, Active Directory security, privilege escalation, web application security, and professional penetration testing methodologies.",
      uz: "2026-yil 2-iyulda xalqaro darajada tan olingan OSCP sertifikatiga ega bo'ldim — bu real hayotiy penetration testing, Active Directory xavfsizligi, imtiyozlarni oshirish (privilege escalation), veb-ilovalar xavfsizligi va professional penetration testing metodologiyalari bo'yicha amaliy tajribamni namoyish etadi.",
      ru: "2 июля 2026 года получил международно признанный сертификат OSCP, подтверждающий практическую экспертизу в реальном penetration testing, безопасности Active Directory, повышении привилегий (privilege escalation), безопасности веб-приложений и профессиональных методологиях penetration testing."
    },

    "tl.present.label": { en: "Present", uz: "Hozir", ru: "Настоящее время" },
    "tl.present.title": { en: "IT Systems Engineer", uz: "IT tizimlar muhandisi", ru: "Инженер IT-систем" },
    "tl.present.desc": {
      en: "Working as an IT Systems Engineer while continuously improving my skills in offensive security, enterprise infrastructure, penetration testing, and security research.",
      uz: "IT tizimlar muhandisi sifatida ishlayotgan bo'lsam-da, hujumkor xavfsizlik, korporativ infratuzilma, penetration testing va xavfsizlik tadqiqotlari bo'yicha ko'nikmalarimni doimiy oshirib bormoqdaman.",
      ru: "Работаю инженером IT-систем, одновременно постоянно развивая навыки в наступательной безопасности, корпоративной инфраструктуре, penetration testing и исследованиях в области безопасности."
    },

    "tl.future": {
      en: "Senior Offensive Security Engineer",
      uz: "Katta hujumkor xavfsizlik muhandisi (Senior Offensive Security Engineer)",
      ru: "Старший инженер по наступательной безопасности (Senior Offensive Security Engineer)"
    },

    "edu.tuit.org": {
      en: "Tashkent University of Information Technologies (TUIT)",
      uz: "Tashkent University of Information Technologies (TUIT)",
      ru: "Tashkent University of Information Technologies (TUIT)"
    },
    "edu.tuit.degree": {
      en: "Bachelor's Degree in Information Security",
      uz: "Axborot xavfsizligi yo'nalishi bo'yicha bakalavr darajasi",
      ru: "Бакалавриат по информационной безопасности"
    },
    "edu.tuit.date": { en: "2024 – Present", uz: "2024 – hozirgacha", ru: "2024 – настоящее время" },
    "edu.tuit.desc": {
      en: "Currently pursuing a Bachelor's degree in Information Security, focusing on cybersecurity, network security, cryptography, digital forensics, secure software development, and enterprise information protection.",
      uz: "Hozirda Axborot xavfsizligi yo'nalishi bo'yicha bakalavriatda tahsil olmoqdaman — kiberxavfsizlik, tarmoq xavfsizligi, kriptografiya, raqamli forensika, xavfsiz dasturiy ta'minot ishlab chiqish va korporativ axborotni himoya qilishga e'tibor qaratilgan.",
      ru: "В настоящее время обучаюсь на бакалавриате по информационной безопасности, с фокусом на кибербезопасность, сетевую безопасность, криптографию, цифровую криминалистику, безопасную разработку программного обеспечения и защиту корпоративной информации."
    },

    "edu.pdp.org": { en: "PDP University", uz: "PDP University", ru: "PDP University" },
    "edu.pdp.degree": {
      en: "Foundation Programme in Cyber Security",
      uz: "Kiberxavfsizlik yo'nalishidagi Foundation Programme",
      ru: "Foundation Programme по кибербезопасности"
    },
    "edu.pdp.date": { en: "2022 – 2024", uz: "2022 – 2024", ru: "2022 – 2024" },
    "edu.pdp.desc": {
      en: "Completed a two-year Foundation Programme in Cyber Security, where I studied university-level coursework instead of the traditional 10th and 11th grades. This programme established a solid academic and practical foundation in computer science, networking, Linux systems, and cybersecurity.",
      uz: "Kiberxavfsizlik yo'nalishidagi ikki yillik Foundation Programme'ni tamomladim — bu davrda an'anaviy 10- va 11-sinflar o'rniga universitet darajasidagi dasturni o'zlashtirdim. Ushbu dastur kompyuter fanlari, tarmoqlar, Linux tizimlari va kiberxavfsizlik bo'yicha mustahkam akademik va amaliy poydevor yaratdi.",
      ru: "Завершил двухлетнюю Foundation Programme по кибербезопасности, в рамках которой вместо традиционных 10 и 11 классов изучал программу университетского уровня. Эта программа заложила прочную академическую и практическую основу в информатике, сетях, системах Linux и кибербезопасности."
    },

    "values.1": { en: "Integrity", uz: "Halollik", ru: "Честность" },
    "values.2": { en: "Discipline", uz: "Intizom", ru: "Дисциплина" },
    "values.3": { en: "Continuous Learning", uz: "Uzluksiz o'rganish", ru: "Непрерывное обучение" },
    "values.4": { en: "Innovation", uz: "Innovatsiya", ru: "Инновации" },
    "values.5": { en: "Curiosity", uz: "Qiziquvchanlik", ru: "Любознательность" },
    "values.6": { en: "Responsibility", uz: "Mas'uliyat", ru: "Ответственность" },
    "values.7": { en: "Precision", uz: "Aniqlik", ru: "Точность" },
    "values.8": { en: "Excellence", uz: "Mukammallik", ru: "Совершенство" },
    "values.9": { en: "Professionalism", uz: "Professionallik", ru: "Профессионализм" },

    "mv.mission": {
      en: "To help organizations strengthen their cybersecurity posture through practical offensive security, continuous learning, and ethical responsibility.",
      uz: "Amaliy hujumkor xavfsizlik, uzluksiz o'rganish va axloqiy mas'uliyat orqali tashkilotlarning kiberxavfsizlik darajasini mustahkamlashga yordam berish.",
      ru: "Помогать организациям укреплять уровень кибербезопасности через практическую наступательную безопасность, непрерывное обучение и этическую ответственность."
    },
    "mv.vision": {
      en: "To become a globally recognized Offensive Security Engineer, contributing to innovative technologies, protecting critical infrastructures, and advancing cybersecurity through research and practical expertise.",
      uz: "Innovatsion texnologiyalarga hissa qo'shadigan, muhim infratuzilmalarni himoya qiladigan va tadqiqot hamda amaliy tajriba orqali kiberxavfsizlikni rivojlantiradigan, dunyo miqyosida tan olingan Offensive Security muhandisiga aylanish.",
      ru: "Стать всемирно признанным инженером по наступательной безопасности, вносящим вклад в инновационные технологии, защиту критической инфраструктуры и развитие кибербезопасности через исследования и практическую экспертизу."
    },

    "closing.philosophy": {
      en: "Security is not about building walls. It is about understanding how attackers think, anticipating emerging threats, and creating resilient systems capable of adapting to an ever-changing digital landscape. I believe that knowledge, discipline, and persistence are the strongest defenses against cyber threats.",
      uz: "Xavfsizlik — devor qurish emas. Bu hujumchilar qanday fikrlashini tushunish, yangi paydo bo'layotgan tahdidlarni oldindan bilish va doimiy o'zgaruvchan raqamli landshaftga moslasha oladigan barqaror tizimlar yaratishdir. Bilim, intizom va matonat kiber tahdidlarga qarshi eng kuchli himoya, deb ishonaman.",
      ru: "Безопасность — это не строительство стен. Это понимание того, как мыслят атакующие, предвидение новых угроз и создание устойчивых систем, способных адаптироваться к постоянно меняющемуся цифровому ландшафту. Я убеждён, что знания, дисциплина и настойчивость — самая сильная защита от киберугроз."
    },
    "closing.quote": {
      en: "“Every vulnerability is an opportunity to learn. Every challenge is an opportunity to grow. Every secure system begins with curiosity, discipline, and the courage to think differently.”",
      uz: "“Har bir zaiflik — o'rganish imkoniyati. Har bir qiyinchilik — o'sish imkoniyati. Har bir xavfsiz tizim qiziquvchanlik, intizom va boshqacha fikrlash jasoratidan boshlanadi.”",
      ru: "“Каждая уязвимость — это возможность научиться. Каждая трудность — это возможность вырасти. Каждая защищённая система начинается с любознательности, дисциплины и смелости мыслить иначе.”"
    },
    "closing.final": {
      en: "“I don't just secure systems. I understand how they break, why they fail, and how to make them resilient against tomorrow's threats.”",
      uz: "“Men shunchaki tizimlarni himoya qilmayman. Men ularning qanday buzilishini, nima uchun ishlamay qolishini va ertangi tahdidlarga bardoshli qilish yo'llarini tushunaman.”",
      ru: "“Я не просто защищаю системы. Я понимаю, как они ломаются, почему дают сбой, и как сделать их устойчивыми к угрозам завтрашнего дня.”"
    },

    "contact.resolved": { en: "5 channels resolved ✓", uz: "5 ta kanal topildi ✓", ru: "Найдено 5 каналов ✓" },
    "contact.role": { en: "Cyber Security Engineer", uz: "Kiberxavfsizlik muhandisi", ru: "Инженер по кибербезопасности" },
    "footer.role": { en: "Cyber Security Engineer", uz: "Kiberxavfsizlik muhandisi", ru: "Инженер по кибербезопасности" }
  };

  var TERMINAL = {
    en: [
      { prompt: "$ whoami", out: "narzullo_muhammad_ali" },
      { prompt: "$ id", out: "roles=(cyber-security-engineer,pentester,it-systems-engineer)" },
      { prompt: "$ cat clearance.txt", out: "OSCP — Offensive Security Certified Professional" },
      { prompt: "$ cat motto.txt", out: "Think Like an Attacker. Protect Like an Engineer." }
    ],
    uz: [
      { prompt: "$ whoami", out: "narzullo_muhammad_ali" },
      { prompt: "$ id", out: "roles=(kiberxavfsizlik-muhandisi,pentester,it-tizimlar-muhandisi)" },
      { prompt: "$ cat clearance.txt", out: "OSCP — Offensive Security Certified Professional" },
      { prompt: "$ cat motto.txt", out: "Hujumchidek fikrla. Muhandisdek himoya qil." }
    ],
    ru: [
      { prompt: "$ whoami", out: "narzullo_muhammad_ali" },
      { prompt: "$ id", out: "roles=(инженер-по-кибербезопасности,пентестер,инженер-it-систем)" },
      { prompt: "$ cat clearance.txt", out: "OSCP — Offensive Security Certified Professional" },
      { prompt: "$ cat motto.txt", out: "Думай как атакующий. Защищай как инженер." }
    ]
  };

  var BOOT = {
    en: [
      "booting secure session...",
      "loading profile: narzullo_muhammad_ali",
      "verifying clearance: OSCP",
      "access granted"
    ],
    uz: [
      "xavfsiz sessiya ishga tushirilmoqda...",
      "profil yuklanmoqda: narzullo_muhammad_ali",
      "ruxsat tekshirilmoqda: OSCP",
      "kirish tasdiqlandi"
    ],
    ru: [
      "запуск защищённой сессии...",
      "загрузка профиля: narzullo_muhammad_ali",
      "проверка допуска: OSCP",
      "доступ разрешён"
    ]
  };

  window.I18N = {
    strings: STRINGS,
    terminal: TERMINAL,
    boot: BOOT,
    t: function (key, lang) {
      var entry = STRINGS[key];
      if (!entry) return null;
      return entry[lang] != null ? entry[lang] : entry.en;
    }
  };
})();
