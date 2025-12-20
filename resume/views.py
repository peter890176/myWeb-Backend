import requests
from django.db.models import Count, Sum
from django.shortcuts import render

# Create your views here.
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .models import Visitor


def _get_client_ip(request):
    """
    從 request 取得使用者 IP，優先使用 HTTP_X_FORWARDED_FOR（經過 Proxy/CDN 時）。
    """
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        # 可能會是 "ip1, ip2, ip3"，取第一個即可
        ip = x_forwarded_for.split(",")[0].strip()
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip


def _lookup_country(ip_address: str):
    """
    透過公開的 IP geolocation API 查詢國家資訊。
    這裡使用 http://ip-api.com，個人專案足夠，如需更穩定可改成付費服務。
    """
    if not ip_address:
        return None, None

    try:
        resp = requests.get(
            f"http://ip-api.com/json/{ip_address}?fields=status,country,countryCode",
            timeout=2,
        )
        data = resp.json()
        if data.get("status") == "success":
            return data.get("country"), data.get("countryCode")
    except Exception:
        # 查詢失敗就不要擋住主流程
        pass
    return None, None


@api_view(["POST"])
def track_visit(request):
    """
    記錄一次造訪：
    - 透過前端送來的 visitor_id 做「去重複」
    - 依 IP 反查國家
    - 將該 visitor 的 visit_count +1

    Request JSON:
    {
        "visitor_id": "<瀏覽器中的隨機 ID>"
    }

    Response JSON 範例：
    {
        "created": true,
        "visitor_id": "...",
        "visit_count": 1,
        "country": "Taiwan",
        "country_code": "TW"
    }
    """
    visitor_id = (request.data.get("visitor_id") or "").strip()
    if not visitor_id or len(visitor_id) > 64:
        return Response(
            {"detail": "Invalid visitor_id"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    ip_address = _get_client_ip(request)
    user_agent = request.META.get("HTTP_USER_AGENT", "")

    visitor, created = Visitor.objects.get_or_create(
        visitor_id=visitor_id,
        defaults={
            "ip_address": ip_address,
            "user_agent": user_agent,
        },
    )

    # 如有需要可以更新 IP / UA（使用者可能換裝置或網路）
    updated = False
    if not created:
        if ip_address and visitor.ip_address != ip_address:
            visitor.ip_address = ip_address
            updated = True
        if user_agent and visitor.user_agent != user_agent:
            visitor.user_agent = user_agent
            updated = True

    # 若尚未有國家資訊且有 IP，就查一次
    if ip_address and not visitor.country:
        country, country_code = _lookup_country(ip_address)
        if country or country_code:
            visitor.country = country
            visitor.country_code = country_code
            updated = True

    # 更新造訪次數
    visitor.visit_count = (visitor.visit_count or 0) + 1

    if created or updated:
        visitor.save()
    else:
        # 只改了 visit_count 也要存
        visitor.save(update_fields=["visit_count", "last_seen"])

    return Response(
        {
            "created": created,
            "visitor_id": visitor.visitor_id,
            "visit_count": visitor.visit_count,
            "country": visitor.country,
            "country_code": visitor.country_code,
        }
    )


@api_view(["GET"])
def visit_stats(request):
    """
    回傳整體統計資訊：
    - total_pageviews：所有訪客累計造訪次數總和
    - unique_visitors：去重複後的訪客數（以 visitor_id 為單位）
    - by_country：依國家分組的統計（每國 unique_visitors 與 pageviews）
    """
    agg = Visitor.objects.aggregate(total_pageviews=Sum("visit_count"))
    total_pageviews = agg["total_pageviews"] or 0
    unique_visitors = Visitor.objects.count()

    country_rows = (
        Visitor.objects.values("country", "country_code")
        .annotate(
            unique_visitors=Count("id"),
            pageviews=Sum("visit_count"),
        )
        .order_by("-pageviews")
    )

    return Response(
        {
            "total_pageviews": total_pageviews,
            "unique_visitors": unique_visitors,
            "by_country": [
                {
                    "country": row["country"] or "Unknown",
                    "country_code": row["country_code"] or "",
                    "unique_visitors": row["unique_visitors"],
                    "pageviews": row["pageviews"],
                }
                for row in country_rows
            ],
        }
    )


@api_view(["GET"])
def resume(request):

    host = request.get_host()
    protocol = "https" if request.is_secure() else "http"
    base_url = f"{protocol}://{host}"

    data = {
        "name": "Yue Wen Peter Li",
        "job": "Full-Stack Developer (Front-End focus)",
        "about": "Dream driven developer. Born in Seattle, raised in Taiwan, studied Computer Science at Northeastern University in Boston. A programmer who loves coffee, cats, memes, and trading.",
        "email": "li.yuew@northeastern.edu",
        "linkedin": "https://www.linkedin.com/in/peter-li-97081429a/",
        "github": "https://github.com/peter890176",
        "profileImage": f"{base_url}/static/images/profile.jpg",
        "portfolio": [
            {
                "id": 1,
                "title": "Mock Stack Overflow",
                "description": "A comprehensive Stack Overflow clone built with MERN stack, featuring question, answer, and voting functionality",
                "technologies": ["React", "Node.js", "Express", "MongoDB"],
                "image": f"{base_url}/static/images/project1.jpg",
                "link": "#",
            },
            {
                "id": 2,
                "title": "Image processing application in Java",
                "description": "Java-based image processing application with multiple filters and transformations, built using OOP principles and design patterns",
                "technologies": ["Java", "Swing GUI", "OOP", "Design Patterns"],
                "image": f"{base_url}/static/images/project2.jpg",
                "link": "#",
            },
            {
                "id": 3,
                "title": "Automated Trash Mapping System",
                "description": "Multi-agent system designed to simulate automated trash collection tasks with territory allocation and dynamic pathfinding",
                "technologies": [
                    "Python",
                    "SciKit-learn",
                    "Matplotlib",
                    "NetworkX",
                    "NumPy",
                    "SciPy",
                ],
                "image": f"{base_url}/static/images/project3.jpg",
                "link": "#",
            },
            {
                "id": 4,
                "title": "Little Lemon Restaurant",
                "description": "Modern restaurant website built with Django and React, featuring reservation system and online ordering capabilities",
                "technologies": ["Django", "DRF", "React", "JavaScript"],
                "image": f"{base_url}/static/images/project4.jpg",
                "link": "#",
            },
            {
                "id": 5,
                "title": "Personal Portfolio Website",
                "description": "A responsive personal portfolio website built with Django backend and React frontend, showcasing projects and skills",
                "technologies": ["Django", "React", "Axios", "Netlify", "Railway"],
                "image": f"{base_url}/static/images/project5.jpg",
                "link": "https://myweb-peterli.netlify.app/",
            },
            {
                "id": 6,
                "title": "Full-Stack E-commerce Platform (SF Shop)",
                "description": "A responsive, feature-rich e-commerce platform with a modern frontend and robust RESTful backend.",
                "technologies": [
                    "React",
                    "Node.js",
                    "MongoDB",
                    "Express",
                    "Tailwind CSS",
                    "JWT",
                ],
                "image": f"{base_url}/static/images/project6.jpg",
                "link": "https://sfshop.netlify.app/",
            },
            {
                "id": 7,
                "title": "Evidence-based Search Station",
                "description": "A full-stack AI-powered platform for semantic search and retrieval-augmented generation (RAG) Q&A on PubMed health insurance literature.",
                "technologies": [
                    "FAISS",
                    "Sentence Transformers",
                    "RAG",
                    "Material-UI",
                    "AWS S3",
                    "Docker",
                    "Netlify",
                    "Railway",
                ],
                "image": f"{base_url}/static/images/project7.jpg",
                "link": "https://hirag.netlify.app/rag",
            },
        ],
        "certificates": [
            {
                "name": "Meta Back-End Developer",
                "issuer": "Meta on Coursera",
                "date": "March 13, 2025",
                "link": "https://coursera.org/share/3775c11d21d5f9220992dc6a7901991e",
            },
            {
                "name": "Meta Front-End Developer",
                "issuer": "Meta on Coursera",
                "date": "September 15, 2024",
                "link": "https://coursera.org/share/009e810073c5ba4fbc0e6469a02b70d3",
            },
            {
                "name": "Google Data Analytics",
                "issuer": "Google on Coursera",
                "date": "September 16, 2021",
                "link": "https://coursera.org/share/3d166611be9d9714f28b16980b6295b6",
            },
        ],
        "education": [
            {
                "institution": "Northeastern University, Boston, MA",
                "department": "Khoury College of Computer Sciences",
                "degree": "Master of Science in Computer Science (General track)",
                "period": "Sep 2023 - Apr 2025",
                "gpa": "GPA: 3.8/4.0",
            },
            {
                "institution": "National Yang Ming Chiao Tung University, Taipei, Taiwan",
                "degree": "Master of Science in Health and Welfare Policy",
                "period": "Sep 2019 - Jan 2023",
                "gpa": "GPA: 4.1/4.3",
            },
            {
                "institution": "Fu-Jen Catholic University, Taipei, Taiwan",
                "degree": "B.A. in Sociology & B.S. in Psychology (Double Degree)",
                "period": "Sep 2014 - Jun 2018",
                "gpa": "GPA: 3.8/4.0",
            },
        ],
        "skills": [
            # Frontend
            "React",
            "Next.js",
            "TypeScript",
            "JavaScript",
            "HTML",
            "CSS",
            "Tailwind CSS",
            "Material-UI",
            "Radix UI",

            # Backend & APIs
            "Node.js",
            "Express.js",
            "Django",
            "Django REST Framework (DRF)",
            "Flask",

            # Languages & Databases
            "Python",
            "Java",
            "MongoDB",
            "MySQL",

            # AI / Search
            "RAG",
            "FAISS",
            "Sentence Transformers",
            "Semantic Search",

            # Cloud & DevOps
            "AWS Lambda",
            "AWS S3",
            "Docker",
            "Netlify",
            "Railway",

            # Testing & Quality
            "Jest",
            "Cypress",
            "ESLint",
        ],
        "cvPdf": "/documents/cv.pdf",
    }
    return Response(data)


@api_view(["GET"])
def project_detail(request, id):
    # Get current host
    host = request.get_host()
    protocol = "https" if request.is_secure() else "http"
    base_url = f"{protocol}://{host}"

    # Project details data
    projects = {
        1: {
            "id": 1,
            "title": "Mock Stack Overflow",
            "description": "A comprehensive Stack Overflow clone built with MERN stack, featuring question, answer, and voting functionality",
            "fullDescription": "A comprehensive web application that replicates Stack Overflow's functionality, allowing users to ask programming questions, provide answers, and participate in community voting. Built using the MERN stack (MongoDB, Express.js, React, Node.js) with a focus on responsive design and robust testing. Foundation Of Software Development Team Project(with John Jacoby).",
            "technologies": [
                "JavaScript",
                "React",
                "Node.js",
                "Express.js",
                "MongoDB",
                "Mongoose",
                "Axios",
                "RESTful API",
                "Jest",
                "Cypress",
            ],
            "image": f"{base_url}/static/images/project1_demo.jpg",
            "features": [
                "User registration and authentication with session management",
                "Question posting with categories",
                "Answer submission with formatting",
                "Upvoting/downvoting system for content",
                "Responsive UI for various devices",
                "RESTful API architecture",
                "Comprehensive testing suite with Jest and Cypress",
                "Docker containerization for deployment",
            ],
            "link": "#",
            "github": "https://github.com/peter890176/courseAssignments/tree/main/courseAssignments/graduate/foundationOfSoftwareDevelopment",
        },
        2: {
            "id": 2,
            "title": "Image processing application in Java",
            "description": "Java-based image processing application with multiple filters and transformations, built using OOP principles and design patterns",
            "fullDescription": "An image processing application built in Java that allows users to apply various filters and transformations to images. The application was designed using object-oriented programming principles and design patterns to ensure maintainability and extensibility. Programming Design Paradigm Course Team Project(with Vasant Tholappa).",
            "technologies": [
                "Java",
                "OOP",
                "Design Patterns",
                "Swing GUI",
                "Image Processing",
            ],
            "image": f"{base_url}/static/images/project2_demo.jpg",
            "imageCaption": "Figure: This user interface demonstrates the before and after comparison of image color correction along with RGB distribution graphs",
            "features": [
                "Image loading and saving",
                "Multiple filter options (grayscale, sepia, blur, etc.)",
                "Image transformations (rotate, flip, resize)",
                "Batch processing",
                "User-friendly GUI",
                "Undo/redo functionality",
            ],
            "link": "#",
            "github": "https://github.com/peter890176/courseAssignments/tree/main/courseAssignments/graduate/programmingDesignParadigm/assignment6",
        },
        3: {
            "id": 3,
            "title": "Automated Trash Mapping System",
            "description": "Multi-agent system designed to simulate automated trash collection tasks with territory allocation and dynamic pathfinding",
            "fullDescription": "This is a multi-agent system designed to simulate automated trash collection tasks. The system operates on a network graph where multiple agents are responsible for collecting targets (representing trash) distributed across different edges, and returning to a central hub when they reach their maximum load capacity. The map is divided into different territories, with each agent responsible for collecting in a specific zone. Foundation Of Foundations Artificial Intelligence Team Project(with Jerry Vogel, Kenton Romero, Hemashree Kilari and Lalit Kishore Payidiparty ) ",
            "technologies": [
                "Python",
                "NetworkX",
                "Matplotlib",
                "NumPy",
                "SciKit-learn",
                "SciPy",
            ],
            "image": f"{base_url}/static/images/project3_demo.jpg",
            "features": [
                "Multi-agent System with Territory Allocation - Uses KMeans clustering to divide the map",
                "Dynamic Pathfinding - Utilizes A* algorithm for efficient path planning",
                "Dynamic Territory Redistribution - Periodically reassesses territory boundaries",
                "Congestion Simulation - Routes experience congestion that affects path planning",
                "Interactive Visualization - Real-time display of agent movements",
                "Realistic Map Generation - Uses Delaunay triangulation for sensible map structures",
                "Agent Load Management - Agents return to hub when full",
                "Intelligent Target Collection Strategy - Prioritizes based on distance and quantity",
                "Simulation Pause and Step Functions - Observe system behavior step-by-step",
            ],
            "link": "#",
            "github": "https://github.com/llamas20/automated-trash-mapper",
        },
        4: {
            "id": 4,
            "title": "Little Lemon Restaurant",
            "description": "Modern restaurant website built with Django and React, featuring reservation system and online ordering capabilities",
            "fullDescription": "Little Lemon is a comprehensive restaurant website built with React that provides an elegant dining experience for customers. The site features a responsive design with intuitive navigation allowing visitors to browse the menu, make table reservations, and place online orders. The application implements Context API for state management, form validation for user inputs, and localStorage for cart persistence. Meta Front-End/Back-End Developer Certificate Project.",
            "technologies": [
                "Django",
                "DRF",
                "React",
                "JavaScript",
                "CSS",
                "HTML",
                "Context API",
                "LocalStorage",
                "Form Validation",
                "Responsive Design",
            ],
            "image": f"{base_url}/static/images/project4_demo.jpg",
            "features": [
                "Responsive design for all device types",
                "Interactive menu with filtering options",
                "Table reservation system with validation",
                "Restaurant information and location mapping",
                "Contact form with validation",
            ],
            "link": "#",
            "github": "https://github.com/peter890176/littleLemon",
        },
        5: {
            "id": 5,
            "title": "Personal Portfolio Website",
            "description": "A responsive personal portfolio website built with Django backend and React frontend, showcasing projects and skills",
            "fullDescription": "This personal portfolio website demonstrates modern web development practices with a decoupled architecture. The backend is built with Django and Django REST Framework to serve resume and project data through a RESTful API. The frontend is developed with React, featuring responsive design for optimal viewing on all devices. The project implements dynamic data loading, smooth navigation, and detailed project showcases.",
            "technologies": [
                "Django",
                "DRF",
                "React",
                "JavaScript",
                "CSS",
                "HTML",
                "Axios",
                "React Router",
                "Railway",
                "Netlify",
            ],
            "image": f"{base_url}/static/images/project5_demo.jpg",
            "features": [
                "Decoupled architecture with Django backend and React frontend",
                "RESTful API for resume and project data",
                "Responsive design for all device types",
                "Dynamic content loading with Axios",
                "Smooth scrolling navigation between sections",
                "Detailed project showcase pages",
                "Education and certification displays",
                "Social media integration",
                "Deployed with Netlify (frontend) and Railway (backend)",
            ],
            "link": "https://myweb-peterli.netlify.app/",
            "github": "https://github.com/peter890176/myWeb-Frontend",
        },
        6: {
            "id": 6,
            "title": "Full-Stack E-commerce Platform (SF Shop)",
            "description": "A responsive, feature-rich e-commerce platform with a modern frontend and robust RESTful backend, delivering a seamless shopping experience through optimized performance, secure authentication, and scalable architecture.",
            "fullDescription": "A responsive, feature-rich e-commerce platform with a modern frontend and robust RESTful backend, delivering a seamless shopping experience through optimized performance, secure authentication, and scalable architecture.",
            "technologies": [
                "React",
                "JavaScript",
                "React Router",
                "Tailwind CSS",
                "Axios",
                "Node.js",
                "Express.js",
                "MongoDB",
                "Mongoose",
                "JWT",
                "bcrypt",
                "CORS",
                "Docker",
                "Netlify",
                "Railway",
            ],
            "image": f"{base_url}/static/images/project6_demo.jpg",
            "features": [
                "Developed a responsive frontend using React, React Router, and Tailwind CSS, implementing product catalog, category filtering, product details, and a state-managed shopping cart with Context API.",
                "Optimized frontend performance using useMemo, useCallback, and React.memo to minimize re-renders, enhancing stability and user experience.",
                "Built a secure RESTful API with Node.js, Express.js, and MongoDB, supporting user management, product catalog, and order processing.",
                "Implemented JWT-based authentication with bcrypt for password encryption and role-based access control (user vs. admin), ensuring secure data exchange via Axios.",
                "Designed MongoDB schemas with Mongoose for complex data relationships, adding server-side pagination and database indexing to improve API scalability and performance.",
                "Engineered core e-commerce logic, including real-time stock updates and precise price calculations handling discounts and floating-point rounding.",
                "Containerized the application with Docker and set up CI/CD pipelines for automated deployment on Netlify (frontend) and Railway (backend), demonstrating DevOps proficiency.",
                "Automated development workflows with Node.js scripts for database seeding and initial admin user setup, streamlining testing and deployment.",
            ],
            "link": "https://sfshop.netlify.app/",
            "github": "https://github.com/peter890176/sf2",
        },
        7: {
            "id": 7,
            "title": "PubMed Health Insurance Semantic Search & RAG QA Platform",
            "description": "A full-stack AI-powered platform for semantic search and retrieval-augmented generation (RAG) Q&A on PubMed health insurance literature.",
            "fullDescription": "A full-stack AI-powered platform for semantic search and retrieval-augmented generation (RAG) Q&A on PubMed health insurance literature.",
            "technologies": [
                "FAISS",
                "Sentence Transformers",
                "RAG",
                "Material-UI",
                "AWS S3",
                "React" "Flask" "Docker",
                "Netlify",
                "Railway",
            ],
            "image": f"{base_url}/static/images/project7_demo.jpg",
            "features": [
                "Semantic Search: Fast, vector-based search over PubMed articles using FAISS and Sentence Transformers.",
                "RAG Q&A: Ask natural language questions and get AI-generated answers with supporting articles.",
                "Multilingual Support: Automatic translation for non-English queries (e.g., Chinese).",
                "Streaming Progress: Real-time progress updates for long-running queries.",
                "Responsive UI: Mobile-friendly, modern Material-UI design.",
                "Cloud Storage: Large data files (FAISS index, articles) are loaded from AWS S3.",
                "Easy Deployment: Dockerized backend, Netlify frontend, and deployment guides for Railway/Render.",
            ],
            "link": "https://hirag.netlify.app/rag",
            "github": "https://github.com/peter890176/HealthInsuranceRAG",
        },
    }

    # Check if project ID exists
    if int(id) in projects:
        return Response(projects[int(id)])
    else:
        return Response(
            {"error": "Project not found"}, status=status.HTTP_404_NOT_FOUND
        )
