EduPulse AI — Engineering Constitution
Version: 4.0
Status: Authoritative
Repository: EduPulse AI
Core System: Prometheus Decision Engine (PDE)


⸻


0. Purpose of This Document
This document is the authoritative engineering, architecture, product, AI, security, SaaS, and development guidance for Claude Code working on the EduPulse AI repository.
Claude Code MUST read and understand this document before making:
	•	code changes
	•	architecture changes
	•	database changes
	•	API changes
	•	infrastructure changes
	•	AI/LLM changes
	•	Prometheus algorithm changes
	•	security changes
	•	SaaS/billing changes
	•	deployment changes
	•	major UI changes
This document is not merely documentation.
It is an engineering constitution.
When implementation decisions are ambiguous, this document provides the default direction.
When requirements conflict, the priority rules defined in this document apply.


⸻


1. Product Identity
1.1 Product
EduPulse AI
EduPulse AI is an adaptive-learning SaaS platform designed to understand a learner’s evolving knowledge state and determine the most useful next learning action.
EduPulse is not primarily a content-generation product.
Its core value is:
Determine what the learner should learn next, based on evidence about what they know, what they have forgotten, and what they can transfer.


⸻


2. Initial Market
The initial target market is:
	•	Türkiye
	•	Turkish-speaking learners
	•	secondary/high-school education
	•	MEB curriculum
	•	Türkiye Yüzyılı Maarif Modeli-compatible educational structure
	•	Physics as the first subject/domain
Physics is the initial vertical because it provides a sufficiently structured domain for validating:
	•	skills
	•	concepts
	•	prerequisites
	•	assessment
	•	evidence
	•	knowledge-state estimation
	•	transfer
	•	retention
	•	adaptive decisions
The architecture MUST NOT hard-code the entire system around Physics.
Physics is the first domain, not the permanent domain.


⸻


3. Long-Term Product Vision
EduPulse should evolve from:
Local Development
        ↓
MVP
        ↓
Private Beta
        ↓
Pilot Teachers
        ↓
Pilot Schools
        ↓
B2C SaaS
        ↓
B2B School SaaS
        ↓
Institution / Course Center SaaS
        ↓
Enterprise Education Platform
        ↓
Large-Scale Adaptive Learning Infrastructure
Potential future customer segments:
	1.	Individual students
	2.	Parents
	3.	Teachers
	4.	Private tutors
	5.	Course centers
	6.	Private schools
	7.	School chains
	8.	Educational publishers
	9.	Universities / preparatory institutions
	10.	Corporate / institutional education organizations


⸻


4. Business Objective
EduPulse is intended to become a commercially strong SaaS business.
Engineering decisions MUST therefore consider:
	•	scalability
	•	recurring revenue
	•	customer retention
	•	product-led growth
	•	institutional sales
	•	low marginal cost
	•	AI cost control
	•	usage metering
	•	tenant isolation
	•	pricing flexibility
	•	feature entitlements
	•	upgrade paths
	•	customer acquisition cost
	•	lifetime value
	•	gross margin
However:
Revenue optimization MUST NOT compromise learner safety, data integrity, educational integrity, security, or Prometheus scientific validity.


⸻


5. Product Positioning
EduPulse MUST NOT be positioned internally or architecturally as:
	•	an AI chatbot
	•	an AI question generator
	•	a generic LMS
	•	a generic recommendation engine
	•	an LLM wrapper
	•	an AI tutor with opaque reasoning
	•	a dashboard full of charts
The primary product proposition is:
Evidence-based adaptive learning.
The product differentiator is the ability to estimate:
	•	what a learner probably knows
	•	how confidently the system knows it
	•	what evidence supports that estimate
	•	what the learner may have forgotten
	•	whether knowledge transfers to unfamiliar contexts
	•	what learning action should happen next
	•	whether the decision is authorized
	•	what happened after the action


⸻


6. Prometheus Identity
Prometheus is the adaptive-learning decision system behind EduPulse.
The primary decision component is:
Prometheus Decision Engine (PDE)
Prometheus is a domain system.
It is NOT an LLM.
It is NOT allowed to become an opaque AI decision-maker.
Prometheus combines:
	•	learner observations
	•	evidence
	•	knowledge-state estimation
	•	educational models
	•	policies
	•	candidate actions
	•	scoring
	•	constraints
	•	authorization
	•	experimentation
	•	outcomes


⸻


7. Core Learning Loop
The fundamental EduPulse learning loop is:
Learner
   ↓
Learning Activity
   ↓
Observation
   ↓
Evidence
   ↓
Knowledge State
   ↓
Decision Policy
   ↓
Candidate Actions
   ↓
Prometheus Decision Engine
   ↓
Decision
   ↓
Decision Authorization
   ↓
Learning Action
   ↓
Outcome
   ↓
New Observation
This loop is the heart of the system.
The architecture MUST preserve the distinction between these stages.


⸻


8. MVP Learning Loop
The first meaningful MVP MUST prove this complete loop:
Student
   ↓
Physics Skill
   ↓
Assessment
   ↓
Observation
   ↓
Evidence
   ↓
Knowledge State
   ↓
Prometheus Decision
   ↓
Next Task
   ↓
Transfer Task
   ↓
Delayed Retention
Initial delayed retention checkpoints:
	•	14 days
	•	28 days
The MVP should be narrow but scientifically coherent.
Do NOT expand into dozens of unrelated features before this loop works reliably.


⸻


9. Local-First Principle
9.1 Absolute Development Rule
EduPulse MUST be fully developable locally.
The initial development environment MUST NOT depend on cloud infrastructure.
Preferred development environment:
Developer Computer
        ↓
WSL2 / Linux
        ↓
Docker Compose
        ↓
EduPulse
The project should be capable of running locally without requiring:
	•	AWS
	•	Azure
	•	GCP
	•	Kubernetes
	•	managed PostgreSQL
	•	managed Redis
	•	external LLM APIs
	•	cloud queues
	•	cloud observability services


⸻


10. Cloud Strategy
Cloud integration is a later phase.
The development sequence is:
LOCAL
  ↓
LOCAL MVP
  ↓
LOCAL VALIDATION
  ↓
PILOT
  ↓
CLOUD STAGING
  ↓
PRODUCTION
Cloud infrastructure MUST NOT be introduced merely because it is considered “production-like.”
First build a correct system.
Then move infrastructure to the cloud.
The architecture MUST therefore avoid unnecessary coupling to:
	•	AWS
	•	Azure
	•	GCP
	•	Vercel
	•	Supabase
	•	Firebase
	•	managed AI providers


⸻


11. Local Infrastructure
The preferred local infrastructure is:
Docker Compose
│
├── web
│   └── Next.js
│
├── api
│   └── FastAPI
│
├── postgres
│   └── PostgreSQL
│
├── redis
│   └── Redis
│
├── ollama
│   └── Local LLM
│
├── n8n
│   └── Automation
│
├── prometheus-engine
│   └── PDE
│
└── monitoring
    ├── Prometheus
    └── Grafana
Additional services MUST NOT be added without a concrete reason.


⸻


12. Architecture Philosophy
Prefer:
simple
explicit
typed
modular
testable
observable
auditable
versioned
reproducible
Avoid:
clever
implicit
opaque
distributed for no reason
AI-generated complexity
premature optimization
premature microservices


⸻


13. Initial Architecture
The default architecture is a modular monolith.
Do NOT begin with a large microservice architecture.
Conceptually:
                 ┌───────────────────────┐
                 │      Next.js Web      │
                 └───────────┬───────────┘
                             │
                             ▼
                 ┌───────────────────────┐
                 │      FastAPI API      │
                 └───────────┬───────────┘
                             │
             ┌───────────────┼────────────────┐
             ▼               ▼                ▼
       Identity          Education       Assessment
             │               │                │
             └───────────────┼────────────────┘
                             ▼
                    Learning State
                             │
                             ▼
                  Prometheus Engine
                             │
                             ▼
                    Decision Layer
                             │
                             ▼
                   Authorization
                             │
                             ▼
                       Next Action
Prometheus MUST remain a clearly defined domain boundary even if implemented inside the same deployment.


⸻


14. When to Introduce a Separate Service
A module should become a separate service only when there is a concrete reason:
	•	independent scaling
	•	computational isolation
	•	deployment independence
	•	security boundary
	•	domain ownership
	•	infrastructure requirement
	•	failure isolation
Do NOT create microservices simply because:
“This is a SaaS.”


⸻


15. API-First Architecture
All major functionality MUST be accessible through well-defined APIs.
Preferred structure:
Frontend
    ↓
API
    ↓
Application Service
    ↓
Domain Logic
    ↓
Repository / Infrastructure
The frontend MUST NOT contain authoritative business logic.


⸻


16. Backend
Backend:
FastAPI
Language:
Python
Preferred:
	•	Python 3.x
	•	type hints
	•	Pydantic
	•	SQLAlchemy 2.x
	•	Alembic
	•	pytest
API routes MUST remain thin.
Do not place complex business logic inside route handlers.


⸻


17. Frontend
Frontend:
Next.js + TypeScript
Preferred:
	•	Next.js
	•	TypeScript
	•	Tailwind CSS
	•	shadcn/ui
The frontend should be:
	•	responsive
	•	accessible
	•	fast
	•	mobile-friendly
	•	student-friendly
	•	teacher-friendly
	•	institution-friendly
Avoid generic “AI dashboard” aesthetics.


⸻


18. Frontend Product Principle
The interface should answer:
Where am I?
What do I know?
What should I do next?
Why?
What changed?
Students should NOT need to understand:
	•	Bayesian inference
	•	posterior distributions
	•	confidence intervals
	•	decision policies
	•	internal Prometheus architecture
Prometheus works behind the interface.


⸻


19. Education Domain
The education domain should support:
Curriculum
   ↓
Subject
   ↓
Topic
   ↓
Concept
   ↓
Skill
   ↓
Prerequisite
   ↓
Assessment
Initial example:
Physics
 └── Mechanics
      └── Force
           └── Newton's Second Law
                ├── Recognition
                ├── Recall
                ├── Application
                ├── Transfer
                └── Retention


⸻


20. Curriculum Compatibility
The system should support:
	•	MEB curriculum
	•	Türkiye Yüzyılı Maarif Modeli
	•	grade level
	•	subject
	•	topic
	•	learning outcome
	•	skill
	•	prerequisite
	•	assessment relationship
Curriculum data MUST be versioned.
Never assume curriculum content is permanently immutable.


⸻


21. Assessment
Assessment MUST be treated as a first-class domain.
Assessment can include:
	•	diagnostic assessment
	•	formative assessment
	•	retrieval practice
	•	application
	•	transfer
	•	delayed retention
Each assessment should preserve enough context to understand:
	•	what was asked
	•	what skill was targeted
	•	difficulty
	•	content version
	•	learner response
	•	evaluation method
	•	evaluation confidence
	•	timestamp


⸻


22. Observation
An Observation is a directly recorded fact.
Example:
Student answered Question Q123 incorrectly.
An observation MUST NOT contain hidden conclusions.
Observation examples:
	•	answer submitted
	•	answer correct
	•	answer incorrect
	•	hint requested
	•	time spent
	•	task completed
	•	transfer failed
	•	retention assessment completed


⸻


23. Evidence
Evidence is an interpreted signal derived from observations.
Example:
Observation:
Student answered a Newton's Second Law question incorrectly.

Evidence:
Negative evidence for mastery of Newton's Second Law.
Observation and Evidence MUST remain separate.
Never store inferred conclusions as if they were raw observations.


⸻


24. Knowledge State
Knowledge state is an evolving estimate.
It is NOT a fact.
Conceptually:
Student
   ↓
Skill
   ↓
Knowledge State
   ├── mastery probability
   ├── confidence
   ├── evidence count
   ├── recency
   ├── retention estimate
   ├── transfer performance
   └── model version
The system MUST avoid simplistic representations such as:
mastery = true
unless there is an explicit reason for a deterministic state.


⸻


25. Bayesian Knowledge Model
The initial Prometheus knowledge-state model should support Bayesian estimation.
Where appropriate, Beta-Binomial modeling should be considered for binary mastery evidence.
Conceptually:
Prior
  +
Evidence
  ↓
Posterior
  ↓
Updated Knowledge State
Potential state:
mastery_probability
confidence
evidence_count
last_observed_at
model_version
The mathematical model MUST be documented before implementation.
Any change to the model requires:
	•	hypothesis
	•	mathematical formulation
	•	assumptions
	•	expected behavior
	•	tests
	•	comparison against previous behavior
	•	consideration of Shadow Mode


⸻


26. Do Not Overclaim Mastery
Prometheus MUST NOT say:
Student definitely knows Skill X.
when the underlying evidence only supports probabilistic inference.
Prefer:
	•	estimated
	•	likely
	•	evidence suggests
	•	high confidence
	•	low confidence
	•	insufficient evidence


⸻


27. Evidence Quality
Evidence should have quality characteristics where appropriate.
Examples:
	•	directness
	•	recency
	•	reliability
	•	task validity
	•	transfer relevance
	•	evaluation confidence
A correct answer to a trivial recognition question should not automatically outweigh multiple high-quality transfer failures.


⸻


28. Recognition / Recall / Application / Transfer / Retention
Prometheus should distinguish:
	1.	Recognition
	2.	Recall
	3.	Application
	4.	Transfer
	5.	Retention
These are not interchangeable.
A learner correctly answering a familiar question MUST NOT automatically be considered to have mastered the underlying skill.


⸻


29. Transfer Tasks
Transfer is a core component of the learning model.
A transfer task should change relevant surface characteristics while preserving the underlying skill.
The system should distinguish:
memorization
      ≠
conceptual understanding
      ≠
transfer
Transfer outcomes must become evidence for the knowledge-state system.


⸻


30. Delayed Retention
Prometheus MUST support delayed retention.
Initial checkpoints:
14 days
28 days
Retention records should preserve:
	•	original learning event
	•	skill/concept
	•	elapsed time
	•	delayed assessment
	•	result
	•	evidence
	•	retention estimate
	•	model version
Never reduce retention to a single unexplained percentage.


⸻


31. Misconceptions
Prometheus should eventually distinguish:
	•	lack of knowledge
	•	retrieval failure
	•	careless error
	•	misconception
	•	transfer failure
	•	retention failure
An incorrect answer MUST NOT automatically become:
misconception = true
Misconception inference requires supporting evidence.


⸻


32. Decision Engine
Prometheus Decision Engine receives structured input:
Learner Context
+
Knowledge State
+
Evidence
+
Educational Policy
+
Available Actions
+
Constraints
and produces:
Decision
The decision MUST be structured.
Example conceptual structure:
decision_id
learner_id
skill_id
selected_action
candidate_actions
scores
reason_codes
policy_version
model_version
confidence
created_at


⸻


33. Decision Explainability
Every important decision should answer:
Why?
The system must be able to trace a decision to:
	•	learner
	•	skill
	•	observations
	•	evidence
	•	knowledge state
	•	model version
	•	policy version
	•	candidate actions
	•	scoring
	•	constraints
	•	authorization result


⸻


34. Candidate Actions
Prometheus should evaluate multiple possible learning actions.
Examples:
	•	new concept explanation
	•	retrieval question
	•	easier task
	•	harder task
	•	transfer task
	•	review task
	•	delayed retention assessment
	•	hint
	•	worked example
	•	teacher intervention
	•	defer decision
	•	insufficient-evidence action
Prometheus should NOT always choose the same action type.


⸻


35. Decision Policy
Separate:
Knowledge State
from:
Decision Policy
The state describes what the system believes.
The policy determines what action should follow.
This separation is mandatory.


⸻


36. Content Strategy vs Learner Policy
Separate:
Content Strategy
What types of learning activities are generally appropriate.
Learner Policy
What is appropriate for this specific learner at this moment.
Do not blindly personalize from sparse evidence.
Population-level educational knowledge and individual telemetry are different evidence sources.


⸻


37. Decision Authorization
Prometheus MUST NOT directly execute unrestricted learner-affecting actions.
Pipeline:
PDE Decision
     ↓
Authorization Layer
     ↓
Allowed?
  ↙     ↘
Yes      No
 ↓        ↓
Execute  Reject/Escalate
Authorization may depend on:
	•	role
	•	tenant policy
	•	educational policy
	•	safety policy
	•	consent
	•	age-related rules
	•	configuration
	•	confidence threshold
	•	feature flags
Decision generation and authorization MUST remain separate.


⸻


38. Shadow Mode
New decision algorithms SHOULD support Shadow Mode.
Real Learner Activity
       ↓
New Prometheus Algorithm
       ↓
Hypothetical Decision
       ↓
Log
The decision does not affect the learner.
Shadow Mode should be used before major decision-policy changes enter active learning flows.


⸻


39. Falsification
Prometheus MUST support the possibility that its assumptions are wrong.
Important hypotheses should be represented explicitly.
Conceptually:
Hypothesis
   ↓
Evidence
   ↓
Prediction
   ↓
Action
   ↓
Outcome
   ↓
Supported / Not Supported / Inconclusive
The system MUST NOT be designed only to confirm existing assumptions.


⸻


40. Event Sourcing / Immutable Telemetry
Important learner activity should be represented as immutable events whenever practical.
Examples:
student.created
lesson.started
lesson.completed
question.presented
answer.submitted
answer.evaluated
hint.requested
feedback.viewed
task.completed
transfer.completed
retention.assessed
decision.generated
decision.authorized
decision.executed
decision.outcome_recorded
Events should preserve:
	•	event ID
	•	tenant ID
	•	actor
	•	subject
	•	timestamp
	•	event type
	•	payload
	•	schema version
	•	correlation ID
	•	provenance
Historical events MUST NOT be silently mutated.


⸻


41. Provenance
Important generated or inferred data MUST preserve provenance.
Examples:
	•	observation that generated evidence
	•	model that evaluated an answer
	•	prompt version
	•	AI provider
	•	AI model
	•	policy version
	•	knowledge-state algorithm version
	•	content version
	•	assessment version
Never remove provenance merely to simplify database design.


⸻


42. Versioning
The following artifacts should be versioned:
	•	API schemas
	•	database schema
	•	event schemas
	•	Prometheus algorithm
	•	decision policies
	•	prompts
	•	AI models
	•	curriculum
	•	content
	•	assessment rules
Historical decisions MUST retain their semantic context.


⸻


43. AI Architecture
LLMs are supporting components.
They are NOT the source of truth for:
	•	learner identity
	•	mastery
	•	authorization
	•	billing
	•	permissions
	•	tenant isolation
	•	historical events
	•	security
	•	financial calculations
Preferred architecture:
EduPulse
    ↓
AI Gateway
    ↓
Model Router
    ├── Ollama
    ├── External Provider A
    ├── External Provider B
    └── Future Models


⸻


44. Local AI First
During local development:
Ollama is the preferred local model interface.
External LLM providers should be optional.
Application business logic MUST NOT depend directly on a particular model provider.


⸻


45. AI Gateway
All production-relevant LLM calls MUST eventually pass through a common AI Gateway.
The gateway should support:
	•	provider selection
	•	model selection
	•	capability detection
	•	prompt versioning
	•	structured output
	•	retries
	•	timeout
	•	fallback
	•	usage accounting
	•	token tracking
	•	cost tracking
	•	safety validation
	•	logging
	•	model metadata


⸻


46. LLM Responsibilities
LLMs may assist with:
	•	question generation
	•	explanation generation
	•	feedback
	•	content drafting
	•	semantic classification
	•	natural-language analysis
	•	teacher assistance
	•	content transformation
LLMs MUST NOT silently replace deterministic logic.


⸻


47. LLM Output
LLM output is untrusted input.
Machine-consumed outputs MUST:
	1.	request structured output
	2.	validate schema
	3.	reject malformed output
	4.	validate educational constraints
	5.	preserve provenance
	6.	record model/prompt versions where appropriate


⸻


48. AI Cost Control
AI cost is a core SaaS concern.
The architecture should support:
cheap deterministic logic
        ↓
local model
        ↓
small external model
        ↓
large external model
Only use expensive models when justified.
Do not send every request to the most expensive model.
AI usage MUST be measurable.


⸻


49. RAG
RAG may be used for:
	•	curriculum material
	•	educational references
	•	institutional documents
	•	approved content
	•	teacher resources
RAG MUST NOT become a substitute for structured educational domain data.
Curriculum structure belongs in structured data.


⸻


50. Multi-Tenant SaaS
EduPulse MUST be multi-tenant from the beginning.
Potential tenant types:
individual
teacher
school
course_center
enterprise
Every tenant-owned entity MUST be tenant-scoped.


⸻


51. Tenant Isolation
Tenant isolation MUST be enforced server-side.
Never trust:
frontend tenant_id
or:
client-provided role
Backend authorization MUST verify ownership/access.
PostgreSQL Row Level Security should be considered for sensitive tables.


⸻


52. Cross-Tenant Security Test
Every major tenant-scoped feature MUST have a negative test:
Tenant A
   ↓
attempts to access
Tenant B resource
   ↓
MUST FAIL
This is mandatory.


⸻


53. Roles
Initial roles:
SUPER_ADMIN
TENANT_ADMIN
SCHOOL_ADMIN
TEACHER
STUDENT
PARENT
Permissions MUST be explicit.
Never assume all users within a tenant can access all data.


⸻


54. Domain Boundaries
Maintain clear boundaries between:
Identity
Tenancy
Education
Curriculum
Assessment
Learning State
Prometheus
AI
Content
Analytics
Billing
Usage
Notifications
Do not create one giant module containing all business logic.


⸻


55. Database
Database:
PostgreSQL
ORM:
SQLAlchemy 2.x
Migration:
Alembic
Rules:
	•	every schema change requires migration
	•	no manual production schema modifications
	•	explicit foreign keys
	•	timezone-aware timestamps
	•	appropriate indexes
	•	stable IDs
	•	constraints for important invariants
	•	historical data must not be casually deleted


⸻


56. Database Deletion Policy
Learner evidence, decisions, and audit records are valuable historical data.
Prefer:
soft deletion
or:
state transition
where appropriate.
Hard deletion MUST be justified.
Privacy/legal deletion requirements MUST still be supported.


⸻


57. Repository Structure
Preferred target structure:
edupulse/
│
├── apps/
│   ├── web/
│   ├── api/
│   └── admin/
│
├── services/
│   └── prometheus-engine/
│
├── packages/
│   ├── shared-types/
│   └── ui/
│
├── ai/
│   ├── gateway/
│   ├── prompts/
│   ├── models/
│   └── rag/
│
├── infrastructure/
│   ├── docker/
│   ├── postgres/
│   ├── redis/
│   ├── monitoring/
│   └── n8n/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── api/
│   └── e2e/
│
├── docs/
│   ├── adr/
│   ├── architecture/
│   ├── api/
│   ├── prometheus/
│   └── product/
│
├── scripts/
│
├── docker-compose.yml
├── .env.example
├── Makefile
├── README.md
└── CLAUDE.md
IMPORTANT:
Before reorganizing the repository, Claude Code MUST inspect the existing structure.
Do NOT perform a large restructuring automatically.


⸻


58. Existing Repository Rule
Before changing architecture:
Inspect
↓
Understand
↓
Document
↓
Plan
↓
Change
Never:
Delete
↓
Rewrite
↓
Hope


⸻


59. SaaS Business Architecture
SaaS functionality MUST be separated from core learning logic.
Core SaaS entities:
Tenant
Plan
Subscription
Entitlement
Usage
Invoice
Payment


⸻


60. Entitlement System
Do NOT scatter checks such as:
if user.plan == "pro":
Use an entitlement system.
Conceptually:
Plan
 ↓
Entitlements
 ↓
Tenant/User
 ↓
Feature Access
This allows pricing plans to evolve without rewriting business logic.


⸻


61. Commercial Model
EduPulse should support several monetization layers.
B2C
Individual student subscription.
Potential tiers:
Free
Student
Student Pro
Teacher
Potential tiers:
Free Teacher
Teacher Pro
Teacher Plus
School
Institutional subscription based on:
	•	active students
	•	teachers
	•	classes
	•	usage
	•	features
Course Center
Subscription based on:
	•	student count
	•	teacher count
	•	usage
	•	analytics
	•	administration
Enterprise
Custom contracts.


⸻


62. Revenue Strategy
The commercial architecture should prioritize:
B2C acquisition
       ↓
Product engagement
       ↓
Teacher adoption
       ↓
Classroom adoption
       ↓
School pilot
       ↓
Institutional contract
       ↓
Expansion
The largest revenue opportunity should ultimately come from B2B/B2B2C institutional customers rather than depending exclusively on individual student subscriptions.


⸻


63. Pricing Philosophy
Pricing should be:
	•	simple
	•	understandable
	•	value-based
	•	scalable
	•	usage-aware
	•	upgrade-friendly
Avoid excessive pricing complexity.
The product should create clear reasons to move upward:
Free
 ↓
Personal
 ↓
Pro
 ↓
Teacher
 ↓
School
 ↓
Enterprise
Pricing MUST remain configurable.
Do not hard-code prices into application logic.


⸻


64. SaaS Unit Economics
The system MUST be capable of measuring:
MRR
ARR
ARPU
ARPA
CAC
LTV
Churn
Retention
Conversion
Activation
Expansion Revenue
Gross Margin
AI Cost per User
AI Cost per Learning Session


⸻


65. Usage Metering
Track where appropriate:
	•	AI requests
	•	token usage
	•	model usage
	•	generated questions
	•	student attempts
	•	assessments
	•	storage
	•	API calls
	•	teacher usage
	•	active learners
Usage records should support:
	•	billing
	•	cost analysis
	•	abuse prevention
	•	product analytics


⸻


66. Product-Led Growth
The B2C product should support a Product-Led Growth model.
The core growth loop should be:
Student joins
     ↓
Diagnostic assessment
     ↓
Receives personalized learning path
     ↓
Sees measurable progress
     ↓
Returns
     ↓
Improves
     ↓
Shares result
     ↓
New student
The product should demonstrate value quickly.


⸻


67. Activation
The first-session experience should aim to reach:
Signup
 ↓
Choose grade
 ↓
Choose subject
 ↓
Diagnostic assessment
 ↓
Initial knowledge map
 ↓
First personalized recommendation
 ↓
First learning action
Avoid lengthy onboarding.


⸻


68. Marketing Strategy
Marketing should be built around the product’s real differentiator.
Do NOT market EduPulse primarily as:
“AI generates unlimited questions.”
Prefer:
“EduPulse learns what the student actually knows and decides what they should study next.”
Marketing pillars:
	1.	Adaptive learning
	2.	Evidence-based progress
	3.	Personalization
	4.	Transfer
	5.	Retention
	6.	Teacher insight
	7.	Measurable improvement


⸻


69. Content Marketing
Potential acquisition channels:
	•	YouTube
	•	SEO
	•	TikTok/short-form video
	•	Instagram
	•	teacher communities
	•	educational blogs
	•	free diagnostic tests
	•	free physics resources
	•	teacher webinars
	•	school demonstrations
	•	referral programs


⸻


70. YouTube Strategy
Physics is the initial domain.
Educational content can be used as a marketing funnel:
YouTube Physics Content
        ↓
Free Diagnostic
        ↓
EduPulse Account
        ↓
Personalized Learning
        ↓
Paid Subscription
The educational content itself should provide genuine value.
It MUST NOT become merely an advertisement.


⸻


71. Teacher Acquisition
Teachers are a strategic distribution channel.
Teacher-facing acquisition should emphasize:
	•	identifying weak skills
	•	identifying students needing attention
	•	seeing improvement
	•	detecting retention problems
	•	assigning targeted activities
	•	reducing assessment workload
Teachers should receive actionable insights, not merely charts.


⸻


72. School Sales
School sales should follow:
Lead
 ↓
Demo
 ↓
Small pilot
 ↓
Measured outcome
 ↓
Case study
 ↓
School-wide deployment
 ↓
Expansion
Pilot design should measure:
	•	activation
	•	engagement
	•	completion
	•	skill improvement
	•	transfer
	•	retention
	•	teacher adoption


⸻


73. Network Effects
Potential future network effects:
	•	teacher-created content
	•	anonymized aggregate learning insights
	•	curriculum analytics
	•	school benchmarking
	•	skill difficulty intelligence
	•	content quality feedback
These must respect privacy and tenant isolation.


⸻


74. Analytics Philosophy
Analytics MUST lead to decisions.
Bad:
37 charts
Good:
12 students are weak in Skill X.
5 have declining retention.
3 require teacher attention.
Recommended intervention: ...


⸻


75. Student Dashboard
Student dashboard should emphasize:
	•	current learning state
	•	progress
	•	next action
	•	completed skills
	•	weak skills
	•	retention
	•	transfer
	•	streak/motivation where educationally appropriate
Avoid overwhelming students with technical metrics.


⸻


76. Teacher Dashboard
Teacher dashboard should answer:
	•	Which students need attention?
	•	Which skills are weak?
	•	Which students are improving?
	•	Which students are forgetting?
	•	Which misconceptions appear?
	•	What should I do next?


⸻


77. Admin Dashboard
Institution administrators should see:
	•	active students
	•	active teachers
	•	adoption
	•	usage
	•	learning outcomes
	•	class performance
	•	retention
	•	system health
	•	subscription
	•	usage
Do not expose unnecessary sensitive learner information.


⸻


78. Security
Security is a first-class requirement.
Minimum expectations:
	•	secure authentication
	•	password hashing
	•	secure token handling
	•	RBAC
	•	tenant isolation
	•	rate limiting
	•	input validation
	•	output validation
	•	SQL injection protection
	•	XSS protection
	•	CSRF protection where applicable
	•	secure headers
	•	secret management
	•	audit logging
	•	dependency auditing
	•	safe file handling


⸻


79. Secrets
Never commit:
.env
API keys
passwords
tokens
private credentials
production secrets
Never put API keys in frontend code.


⸻


80. Privacy
EduPulse may process sensitive learner information.
Follow:
	•	data minimization
	•	purpose limitation
	•	least privilege
	•	access control
	•	auditability
	•	retention policies
	•	secure deletion where legally required
Do not collect data merely because it is technically possible.
Every new telemetry field should have a documented purpose.


⸻


81. Child / Minor Safety
Because the target market includes secondary/high-school learners, the system must treat minors as a potential user population.
Design must consider:
	•	parental relationships
	•	teacher oversight
	•	institutional permissions
	•	consent
	•	age-related policies
	•	privacy
	•	data minimization
	•	safe AI outputs
High-impact educational decisions should remain reviewable.


⸻


82. AI Educational Safety
AI-generated content can be incorrect.
Important educational outputs should support:
	•	validation
	•	provenance
	•	teacher review
	•	structured constraints
	•	content versioning
Never assume:
“The LLM said it confidently, therefore it is correct.”


⸻


83. Observability
Production architecture should support:
Metrics
Logs
Traces
Errors
Audit Events
Decision Logs
Potential tooling:
	•	Prometheus
	•	Grafana
	•	Loki
	•	Sentry
Local development should remain lightweight.


⸻


84. Logging
Never log unnecessarily:
	•	passwords
	•	API keys
	•	tokens
	•	full learner-sensitive data
	•	confidential institutional data
Logs should contain enough context for debugging without becoming a privacy risk.


⸻


85. Decision Logging
Important Prometheus decisions should answer:
Who?
Which learner?
When?
Which skill?
Which evidence?
Which knowledge state?
Which model?
Which policy?
Which candidates?
Why?
Was it authorized?
What happened afterward?


⸻


86. Testing Strategy
Testing layers:
Unit
 ↓
Integration
 ↓
API
 ↓
E2E
Prometheus requires additional testing for:
	•	mathematical correctness
	•	Bayesian updates
	•	edge cases
	•	temporal behavior
	•	decision reproducibility
	•	policy behavior
	•	authorization
	•	Shadow Mode
	•	falsification
	•	transfer
	•	retention


⸻


87. Property-Based Testing
Where mathematically appropriate, use property-based testing.
Examples:
	•	probabilities remain within valid ranges
	•	Bayesian updates behave monotonically under defined assumptions
	•	impossible values are rejected
	•	timestamps behave correctly
	•	decisions remain reproducible


⸻


88. Cross-Tenant Tests
Every important tenant-scoped feature should include:
positive access test
negative cross-tenant access test
role permission test


⸻


89. API Testing
API tests should cover:
	•	authentication
	•	authorization
	•	validation
	•	tenant isolation
	•	error behavior
	•	idempotency where required
	•	pagination
	•	filtering
	•	rate limits where applicable


⸻


90. Error Handling
Errors MUST be:
	•	explicit
	•	typed
	•	observable
	•	safe
	•	actionable
Do not expose:
	•	stack traces
	•	SQL errors
	•	internal paths
	•	credentials
	•	implementation details
Do not silently swallow exceptions.


⸻


91. Docker
Local development should work with:
docker compose up -d
Services should have:
	•	health checks
	•	persistent volumes where required
	•	predictable names
	•	isolated networks where appropriate


⸻


92. n8n
n8n is an automation/orchestration component.
Use n8n for:
	•	workflows
	•	scheduled tasks
	•	notifications
	•	integrations
	•	content pipelines
	•	administrative automation
Do NOT put core Prometheus logic inside n8n.
Prometheus logic belongs in application/domain code.
n8n is not the source of truth.


⸻


93. Redis
Redis may be used for:
	•	caching
	•	rate limiting
	•	temporary state
	•	queues
	•	background workloads
Redis MUST NOT become the authoritative database for historical learner state.


⸻


94. Background Jobs
Use background workers for genuinely asynchronous workloads such as:
	•	delayed retention scheduling
	•	content generation
	•	analytics aggregation
	•	notifications
	•	expensive processing
Do not move ordinary synchronous business logic into background jobs without reason.


⸻


95. Billing Isolation
Billing MUST remain separate from learning logic.
The Prometheus engine must not know whether a learner is:
	•	Free
	•	Pro
	•	Enterprise
The entitlement system determines whether a feature is available.


⸻


96. Feature Flags
Use feature flags for:
	•	experimental algorithms
	•	Shadow Mode
	•	new UI
	•	new AI models
	•	pricing experiments
	•	pilot-school features
Do not use scattered hard-coded flags throughout the application.


⸻


97. Experimentation
Experiments should be:
	•	explicit
	•	versioned
	•	measurable
	•	reversible
Examples:
	•	decision-policy experiment
	•	question difficulty experiment
	•	onboarding experiment
	•	pricing experiment
	•	recommendation strategy experiment
Never silently experiment on production learners.


⸻


98. Prometheus Scientific Integrity
Prometheus is the intellectual core of the product.
Therefore:
Do not casually change the mathematical model.
Before changing Prometheus:
	1.	Define the problem.
	2.	State the hypothesis.
	3.	Define mathematical formulation.
	4.	Define assumptions.
	5.	Define expected behavior.
	6.	Implement tests.
	7.	Compare against previous behavior.
	8.	Consider Shadow Mode.
	9.	Document the change in an ADR.


⸻


99. Reproducibility
Given the same:
observations
evidence
knowledge state
model version
policy version
configuration
Prometheus should produce the same decision unless stochastic behavior is explicitly designed and recorded.
Randomness MUST be controlled where reproducibility is required.


⸻


100. Decision Provenance
Every important decision should preserve:
decision_id
tenant_id
learner_id
skill_id
input_state_version
evidence_ids
candidate_actions
scores
selected_action
reason_codes
model_version
policy_version
authorization_result
timestamp


⸻


101. Architecture Decision Records
Significant decisions MUST be recorded in:
docs/adr/
Initial ADRs:
ADR-001-modular-monolith.md
ADR-002-multi-tenancy.md
ADR-003-event-sourcing.md
ADR-004-bayesian-knowledge-state.md
ADR-005-prometheus-decision-engine.md
ADR-006-ai-gateway.md
ADR-007-shadow-mode.md
ADR-008-transfer-retention.md
ADR-009-saas-entitlements.md
ADR-010-local-first-development.md
Each ADR:
Context
Decision
Alternatives
Consequences


⸻


102. Documentation
Architecture documentation is part of implementation.
If code changes architecture:
Code
+
Tests
+
Documentation
must remain consistent.
Never allow architecture documents and implementation to silently diverge.


⸻


103. Git Strategy
Use small meaningful commits.
Preferred prefixes:
feat:
fix:
refactor:
test:
docs:
chore:
security:
perf:
Do not mix unrelated changes.
Never perform destructive Git operations without explicit instruction.
Never rewrite history unless explicitly requested.


⸻


104. Dependency Policy
Before adding a dependency:
	1.	Check whether existing dependencies already provide the functionality.
	2.	Check maintenance status.
	3.	Check licensing.
	4.	Check security implications.
	5.	Check package size.
	6.	Check complexity.
	7.	Prefer mature libraries.
Do not add dependencies merely for convenience.


⸻


105. No Fake Implementations
Never create fake functionality merely to make tests pass.
Forbidden:
	•	hardcoded AI responses
	•	fake production database results
	•	fake business logic
	•	silent fallback behavior
	•	TODOs pretending to be implementation
Mocks belong in tests.
If a feature is incomplete, mark it explicitly.


⸻


106. No Hidden Behavior
Do not introduce:
	•	undocumented background jobs
	•	hidden transformations
	•	implicit permission escalation
	•	undocumented AI calls
	•	undocumented model changes
	•	silent data deletion
	•	hidden external API calls
Important behavior must be visible in:
	•	code
	•	configuration
	•	documentation
	•	tests


⸻


107. Backward Compatibility
Before changing:
	•	database schemas
	•	API contracts
	•	event schemas
	•	decision schemas
inspect existing persisted data and consumers.
Prefer:
additive migration
over:
destructive migration


⸻


108. Configuration
Use environment variables.
Provide:
.env.example
Environment separation:
development
test
staging
production
Never commit secrets.


⸻


109. Performance
Do not optimize prematurely.
Priority:
Correctness
 ↓
Security
 ↓
Maintainability
 ↓
Observability
 ↓
Performance
Performance optimizations should be measurement-driven.


⸻


110. Product Metrics
The product should eventually track:
Acquisition
	•	visitors
	•	signup conversion
	•	diagnostic-start rate
Activation
	•	diagnostic completion
	•	first recommendation
	•	first learning action
Engagement
	•	weekly active learners
	•	monthly active learners
	•	learning sessions
	•	tasks completed
Learning
	•	skill improvement
	•	transfer performance
	•	retention
	•	time to mastery estimate
Monetization
	•	free-to-paid conversion
	•	MRR
	•	ARR
	•	ARPU
	•	churn
	•	expansion
B2B
	•	pilot conversion
	•	teacher activation
	•	school activation
	•	student activation
	•	renewal
	•	expansion


⸻


111. North Star Metric
A candidate North Star Metric is:
Learners receiving and completing appropriate next learning actions that produce measurable improvement.
Do NOT optimize purely for:
	•	screen time
	•	number of questions
	•	number of AI calls
	•	chatbot messages
Engagement without learning value is not the objective.


⸻


112. Growth Metrics Must Not Corrupt Learning
The system MUST NOT optimize engagement at the expense of learning.
Avoid:
	•	unnecessary notifications
	•	artificial streak manipulation
	•	infinite question generation
	•	addictive loops without educational purpose
The product should optimize:
Learning Outcome
+
Retention
+
User Value
+
Sustainable Engagement


⸻


113. Initial Development Priority
The implementation order is:
P0
Foundation
Docker
Database
API
Frontend
Testing

P1
Identity
Tenant
RBAC

P2
Education Model
Curriculum
Subject
Topic
Skill
Prerequisites

P3
Assessment
Questions
Attempts
Observations
Evidence

P4
Knowledge State
Bayesian Engine

P5
Prometheus Decision Engine

P6
Transfer
Retention 14d/28d
Falsification

P7
AI Gateway
Ollama
LLM
RAG
Content Generation

P8
Student Dashboard
Teacher Dashboard
Admin Dashboard

P9
Usage
Entitlements
Billing
SaaS

P10
Security Hardening
Observability
Performance
Load Testing
Cloud Deployment
Production


⸻


114. What NOT to Build Early
Do NOT prioritize:
	•	Kubernetes
	•	complex microservices
	•	elaborate billing
	•	enterprise SSO
	•	advanced recommendation algorithms
	•	dozens of subjects
	•	social networking
	•	gamification systems
	•	mobile native apps
	•	unnecessary AI agents
	•	complex vector infrastructure
	•	large-scale cloud infrastructure
until the core adaptive-learning loop works.


⸻


115. MVP Definition
The MVP is successful if:
Student
 ↓
Physics Skill
 ↓
Assessment
 ↓
Observation
 ↓
Evidence
 ↓
Knowledge State
 ↓
Prometheus Decision
 ↓
Next Task
 ↓
Transfer
 ↓
Retention
works end-to-end with:
	•	persistent data
	•	reproducible decisions
	•	explainability
	•	tests
	•	authorization
	•	provenance


⸻


116. MVP Does NOT Require
The MVP does not need:
	•	full enterprise billing
	•	every curriculum
	•	every subject
	•	mobile apps
	•	advanced marketing automation
	•	cloud-native infrastructure
	•	Kubernetes
	•	dozens of AI providers
The goal is to validate the learning engine.


⸻


117. Commercial Validation
After the core MVP:
MVP
 ↓
10–20 students
 ↓
teacher feedback
 ↓
50–100 students
 ↓
pilot classroom
 ↓
pilot school
 ↓
paid pilot
The system should be instrumented so learning outcomes and product usage can be measured from the beginning.


⸻


118. SaaS Expansion Strategy
The long-term product should support:
B2C
 ↓
Teacher
 ↓
School
 ↓
Institution
 ↓
Enterprise
The same Prometheus engine should power all tiers.
Only:
	•	permissions
	•	features
	•	entitlements
	•	analytics
	•	content scope
	•	usage limits
should vary by commercial model.


⸻


119. Architecture Must Support Future Cloud
Although cloud is delayed, the architecture MUST remain cloud-migratable.
Avoid assumptions such as:
localhost-only database logic
filesystem-only state
provider-specific business logic
single-machine assumptions in domain code
Local-first does NOT mean local-only.


⸻


120. Cloud Migration Principle
Future migration should primarily replace infrastructure adapters:
Local PostgreSQL
       ↓
Managed PostgreSQL

Local Redis
       ↓
Managed Redis

Ollama
       ↓
External AI Provider

Docker Compose
       ↓
Cloud Deployment
Domain logic should remain substantially unchanged.


⸻


121. Claude Code Operating Protocol
Before modifying code:
Step 1
Read:
CLAUDE.md
Step 2
Inspect repository structure.
Step 3
Identify relevant files.
Step 4
Read existing implementation.
Step 5
Read related tests.
Step 6
Check documentation and ADRs.
Step 7
Understand dependencies.
Step 8
Formulate implementation plan.
Step 9
Implement the smallest coherent change.
Step 10
Run tests.
Step 11
Review diff.
Step 12
Update documentation if required.


⸻


122. Mandatory Pre-Implementation Report
For non-trivial tasks Claude Code should first report:
UNDERSTANDING

PLAN

FILES AFFECTED

DATABASE IMPACT

API IMPACT

PROMETHEUS IMPACT

SECURITY RISKS

TEST PLAN

DOCUMENTATION IMPACT

ROLLBACK / RISK NOTES
Then implement.
For small and obvious changes, this report may be abbreviated.


⸻


123. Repository Inspection Rule
Claude Code MUST NOT assume that the repository matches the desired architecture.
It must inspect:
tree
source files
Docker configuration
database models
migrations
API routes
frontend
tests
environment files
documentation
Git status
before major changes.


⸻


124. Do Not Rewrite Existing Work Blindly
Never:
	•	delete existing implementation without understanding it
	•	replace architecture wholesale
	•	regenerate the entire backend
	•	regenerate the entire frontend
	•	recreate the database
	•	destroy migrations
	•	replace working code with generic templates
unless explicitly authorized.


⸻


125. Task Size
Prefer small vertical slices.
Example:
Skill
 ↓
Database
 ↓
API
 ↓
Test
rather than implementing 15 disconnected entities simultaneously.


⸻


126. Vertical Slice Principle
A feature should ideally move through:
Domain
 ↓
Database
 ↓
Application Service
 ↓
API
 ↓
Frontend
 ↓
Tests
This provides working increments.


⸻


127. Migration Rule
Every database schema change requires:
Alembic migration
Never manually alter production schemas.
Migrations must be reviewed.
Destructive migrations require explicit justification.


⸻


128. API Contract Rule
API contracts should use:
	•	Pydantic
	•	explicit schemas
	•	typed responses
	•	validation
	•	versioning where appropriate
Avoid returning arbitrary dictionaries when a typed schema is practical.


⸻


129. Internal Communication
Prefer:
typed structured data
over:
natural language
for service-to-service communication.
Use:
	•	Pydantic
	•	JSON Schema
	•	enums
	•	versioned event schemas
Natural language is for users and AI interfaces, not internal contracts.


⸻


130. Idempotency
Operations that may be retried MUST be designed for idempotency where appropriate.
Especially:
	•	event ingestion
	•	payment operations
	•	webhook processing
	•	background jobs
	•	external provider calls


⸻


131. Auditability
Important actions should generate audit records.
Examples:
	•	permission changes
	•	role changes
	•	tenant changes
	•	important decisions
	•	policy changes
	•	billing changes
	•	content approval
	•	AI configuration changes


⸻


132. Data Integrity
The system should prefer database constraints over application assumptions where practical.
Examples:
	•	foreign keys
	•	unique constraints
	•	check constraints
	•	non-null requirements
	•	tenant-scoped uniqueness


⸻


133. Security Priority
If a feature conflicts with security:
Security wins.
If a feature conflicts with data integrity:
Data integrity wins.
If a feature conflicts with Prometheus scientific integrity:
Scientific integrity wins.


⸻


134. Requirement Conflict Priority
The priority order is:
1. Security
2. Privacy
3. Data Integrity
4. Correctness
5. Prometheus Scientific Integrity
6. Educational Safety
7. Maintainability
8. Testability
9. Observability
10. Performance
11. Developer Convenience
12. UI Polish


⸻


135. What Claude Code MUST NOT Do
Without explicit approval:
	•	delete the existing project
	•	rewrite architecture wholesale
	•	destroy migrations
	•	perform destructive database operations
	•	introduce Kubernetes
	•	introduce unnecessary microservices
	•	change Prometheus mathematics
	•	remove event sourcing
	•	remove provenance
	•	bypass authorization
	•	weaken tenant isolation
	•	add secrets
	•	send learner data to external services
	•	replace deterministic logic with LLM calls
	•	change production infrastructure
	•	add unnecessary large dependencies
	•	introduce hidden background jobs
	•	introduce undocumented AI calls


⸻


136. External Data Transfer
Before sending learner data to an external service, Claude Code MUST verify:
	•	necessity
	•	privacy implications
	•	authorization
	•	tenant policy
	•	data minimization
	•	configuration
	•	provider requirements
External AI calls should not be silently introduced.


⸻


137. Production Readiness
Production readiness requires:
Correctness
+
Security
+
Privacy
+
Tenant Isolation
+
Authorization
+
Testing
+
Observability
+
Backups
+
Migration Strategy
+
Incident Handling
+
Cost Controls
+
Documentation


⸻


138. Production Deployment
Production deployment is a later phase.
Before cloud deployment:
	1.	local system stable
	2.	integration tests stable
	3.	E2E tests stable
	4.	security review
	5.	tenant isolation tests
	6.	load tests
	7.	backup strategy
	8.	migration strategy
	9.	observability
	10.	cost analysis
	11.	privacy review
	12.	deployment documentation


⸻


139. Cost Architecture
The system must eventually make it possible to answer:
How much does one active learner cost us?

How much does one learning session cost?

How much does one AI-generated question cost?

How much does one school cost to serve?

What is gross margin per plan?
AI cost MUST NOT be treated as invisible infrastructure.


⸻


140. AI Model Routing Strategy
Potential routing:
Deterministic
    ↓
Local model
    ↓
Low-cost external model
    ↓
High-capability model
Routing should consider:
	•	task complexity
	•	quality requirement
	•	latency
	•	cost
	•	privacy
	•	model capability


⸻


141. Product Differentiation
The moat should increasingly come from:
Learner Evidence
       +
Knowledge-State Model
       +
Decision Engine
       +
Transfer Data
       +
Retention Data
       +
Educational Domain Model
not simply from access to an LLM.


⸻


142. Data Flywheel
Long-term product advantage may emerge from:
More learners
      ↓
More observations
      ↓
Better evidence
      ↓
Better knowledge-state estimates
      ↓
Better decisions
      ↓
Better learning outcomes
      ↓
Higher retention
      ↓
More learners
This flywheel MUST remain privacy-preserving and scientifically validated.


⸻


143. Avoid Data Hoarding
More data does not automatically mean better AI.
Every telemetry field must have:
	•	purpose
	•	owner
	•	retention strategy
	•	privacy rationale
	•	analytical value


⸻


144. Educational Outcome Over Engagement
The primary question is:
Did the learner learn?
not:
Did the learner spend more time in the application?
Engagement metrics should support learning outcomes, not replace them.


⸻


145. Product Quality Gate
Before calling a feature “complete”, verify:
[ ] Implementation
[ ] Database migration if required
[ ] Validation
[ ] Unit tests
[ ] Integration tests
[ ] API tests
[ ] Security tests
[ ] Tenant isolation tests
[ ] Observability
[ ] Documentation
[ ] Provenance where applicable
[ ] Versioning where applicable
[ ] No secrets
[ ] No unrelated regressions


⸻


146. Definition of Done
A task is complete only when:
	•	requested behavior exists
	•	architecture remains coherent
	•	domain boundaries remain intact
	•	tenant isolation is preserved
	•	authorization is correct
	•	tests pass
	•	migrations exist where required
	•	errors are handled
	•	observability is adequate
	•	documentation is updated where required
	•	no secrets are introduced
	•	no unrelated behavior is broken


⸻


147. Definition of Done for Prometheus
A Prometheus change is complete only when:
Mathematical formulation
+
Assumptions
+
Implementation
+
Unit tests
+
Edge-case tests
+
Reproducibility tests
+
Decision explanation
+
Versioning
+
Provenance
+
Shadow-mode consideration
are addressed.


⸻


148. Definition of Done for AI
An AI feature is complete only when:
Provider abstraction
+
Structured output
+
Validation
+
Timeout
+
Retry
+
Cost tracking
+
Usage tracking
+
Prompt version
+
Model version
+
Safety validation
+
Fallback behavior
are addressed where applicable.


⸻


149. Definition of Done for SaaS
A SaaS feature is complete only when:
Tenant scope
+
Authorization
+
Entitlement
+
Usage metering
+
Billing implications
+
Auditability
+
Security
+
Testing
are considered.


⸻


150. Final Engineering Principle
EduPulse must be built as a serious software and educational intelligence system.
Not as:
“an AI-generated application.”
Not as:
“a chatbot with a database.”
Not as:
“an unlimited question generator.”
The product is:
An evidence-driven adaptive learning system that determines what a learner should learn next based on what they know, what they may have forgotten, and what they can transfer.
The engineering philosophy is:
Simple
Explicit
Typed
Tested
Observable
Auditable
Versioned
Reproducible
Secure
over:
Clever
Implicit
Opaque
Fragile
Over-engineered
AI-dependent
The architectural journey is:
LOCAL
   ↓
MVP
   ↓
VALIDATION
   ↓
PILOT
   ↓
B2C
   ↓
SCHOOL SaaS
   ↓
B2B
   ↓
CLOUD
   ↓
PRODUCTION
   ↓
SCALE
The ultimate objective is not merely to make EduPulse work.
The objective is to build a defensible adaptive-learning platform whose:
	•	learning model
	•	evidence system
	•	Prometheus decision engine
	•	educational intelligence
	•	learner data
	•	teacher workflows
	•	SaaS infrastructure
	•	and product experience
can evolve into a commercially sustainable, scientifically credible and technically robust education platform.


⸻


END OF CLAUDE.md


