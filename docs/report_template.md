# Flashcard Quizzer CLI Project Report

## Executive Summary

The Flashcard Quizzer is a command-line Python application designed to help users study terminology using flashcard decks stored as JSON files. The final application supports sequential, random, and adaptive quiz modes, validates multiple JSON input formats, provides immediate feedback to users, tracks quiz performance, and handles common errors gracefully. The implementation was deliberately modular so individual components can be tested, maintained, and extended independently.

AI collaboration was central to the development process. I used Claude Code as an implementation assistant while retaining responsibility for defining requirements, reviewing generated code, identifying problems, directing refinements, and verifying results. Rather than considering generated code correct simply because it compiled, the project used automated tests, coverage analysis, linting, and manual review as quality gates. Final verification produced 208 passing tests with 0 failures, 99% code coverage, and 0 flake8 errors.

## Project Overview

### Problem Statement

The goal was to create a lightweight terminal application that allows users to study flashcards without requiring a graphical interface. The application needed to load external data rather than hard-code questions and support different algorithms for determining question order.

An additional goal was software maintainability. The code therefore needed separation of concerns, type hints, automated testing, graceful error handling, and established design patterns.

### Solution Approach

The application separates data loading, models, quiz strategies, statistics, display, session management, and CLI behavior.

Two JSON formats are supported:

[
  {"front": "HTTP", "back": "Hypertext Transfer Protocol"}
]

and:

{
  "cards": [
    {"front": "HTTP", "back": "Hypertext Transfer Protocol"}
  ]
}

A QuizMode abstraction provides a common interface for the three quiz algorithms. SequentialMode, RandomMode, and AdaptiveMode implement different selection behavior, while a factory encapsulates selection of the appropriate strategy.

It also includes argument parsing, case-insensitive answers, colored feedback, statistics, and graceful termination.

## AI Collaboration Experience

### AI Tools Used

The primary coding assistant was Claude Code, running directly inside the provided development workspace. I used the assistant to inspect the repository, generate implementation code, create tests, identify defects, and perform verification.

### Collaboration Workflow

My intended workflow followed the sequence decompose, generate, review, refine, verify. Requirements were broken into areas such as data ingestion, quiz strategies, CLI interaction, and testing.

One lesson emerged immediately: scope control matters. The initial repository-analysis request explicitly asked the AI not to modify files, but Claude progressed into implementation. I stopped the operation, assessed what had been produced, and changed subsequent prompts to tightly constrained requests with explicit limitations.

Later prompts specified not only what Claude should do, but also what it should not do. This produced a more controlled collaboration process and reduced unnecessary AI usage.

### Most Valuable AI Interactions

#### 1. Repository analysis and initial implementation

The first interaction was intended to inspect the starter repository and recommend an architecture. Claude instead progressed through several implementation phases before being interrupted. Although this exceeded the requested scope, it generated substantial usable functionality. I reviewed the resulting state before permitting further changes rather than simply allowing autonomous development to continue.

#### 2. Data validation

Claude created the flashcard data-loading and validation layer and associated tests. The implementation handled both JSON structures and invalid data, ensuring missing files, invalid JSON, or malformed cards did not expose raw Python tracebacks.

#### 3. Adaptive quiz behavior

Adaptive mode required more reasoning than simple sequential or randomized selection. During testing, Claude initially encountered behavior involving a two-card deck and a no-repeat constraint. The AI recognized that the test's assumption was incorrect because strict alternation prevented the weighting behavior from appearing in that scenario. The test was corrected rather than incorrectly changing valid production logic.

The adaptive implementation also incorporated a termination cap so repeatedly answering a card incorrectly could not result in an endless quiz session.

#### 4. Session and CLI testing

During session testing, a constructor had been corrupted during a generated edit. Interestingly, flake8 did not identify the problem because the malformed expression was still syntactically valid Python. A smoke test exposed the defect, and Claude corrected it. This showed why static checks alone are insufficient.

Another testing issue appeared because QuizSession bound input as a default argument at definition time, preventing ordinary monkeypatching of builtins.input. Testing was adjusted through dependency injection at the CLI's QuizSession reference rather than changing production behavior solely to satisfy the test.

#### 5. Final verification

The final verification prompt deliberately prohibited feature additions and refactoring. Claude was directed only to finish the CLI integration, add necessary missing tests, and run quality checks. The resulting suite reported 208 tests passed, 0 failed, 99% coverage, and a clean flake8 result.

## Software Engineering Practices

### Code Quality Measures

The codebase uses modular components, type hints, consistent formatting, linting, error handling, and automated tests. flake8 was used as the final linting quality gate and reported zero errors. The project configuration also supports additional development tooling.

### Testing Strategy

Testing included unit tests for individual modules and integration testing across application behavior. Required scenarios included valid JSON loading, invalid JSON, missing required fields, strategy creation, adaptive behavior, and complete quiz sessions.

The final automated suite contained 208 passing tests and achieved 99% coverage, substantially exceeding the required 80% threshold. The remaining uncovered code consisted primarily of difficult-to-trigger operating-system error paths and the main.py execution guard.

### Design Patterns

The primary architectural pattern is the Strategy Pattern. All quiz modes perform the same broad responsibility, selecting flashcards, while implementing different algorithms. This enables a new strategy such as spaced repetition to be introduced without rewriting the session engine.

A Factory Pattern complements the strategy abstraction by translating a selected mode into the correct strategy implementation. This keeps construction logic out of the primary application workflow.

## Technical Challenges and Solutions

### Challenge 1: Defining Adaptive Behavior

“Prioritize cards the user previously got wrong” leaves implementation decisions unspecified. A naïve implementation could continuously repeat incorrect cards and potentially never terminate.

The solution incorporated weighted prioritization and a bounded retry behavior. Testing exposed interactions between weighting and repeat-prevention rules and helped refine expectations without unnecessarily changing correct logic.

The key lesson was that natural-language requirements often hide edge cases. Asking how an algorithm terminates and how it behaves under repeated failure is essential.

### Challenge 2: Generated Code That Passes Static Checks

A generated constructor was accidentally malformed during an edit. Because the resulting expression was still legal Python syntax, flake8 did not catch it.

A functional smoke test exposed the problem. This reinforced the need for layered verification: linting measures one aspect of quality, while unit and integration tests verify actual behavior.

## Code Quality Analysis

Final verification produced:

- 208 automated tests passed
- 0 automated tests failed
- 99% code coverage
- 0 flake8 errors

I would rate code readability 5/5, maintainability 5/5, test quality 5/5, and documentation 4/5.

## Learning Outcomes

### Technical Skills Developed

This project strengthened my understanding of Python CLI development, JSON validation, Strategy and Factory patterns, dependency injection, testing, coverage, and linting.

### AI Collaboration Skills

The most important AI lesson was that specificity and verification matter more than simply generating more code. Broad prompts can cause an agent to exceed scope. Shorter, constrained prompts were much more effective later in development.

I also learned to distinguish between an AI-generated test failure and an actual product defect. Sometimes the production implementation needs correction, but sometimes the test itself contains an invalid assumption.

## Reflection

### What Worked Well

The strongest element of the project was iterative verification. Automated tests repeatedly exposed issues that static analysis alone would not have detected. Separating quiz algorithms using Strategy and Factory patterns also produced an architecture appropriate for future extensions.

### What Could Be Improved

The initial AI prompt should have been narrower and more strongly constrained. Claude began implementing functionality despite initially being asked only to inspect the repository. Future work should use smaller task boundaries from the start and verify repository changes between phases.

Testability could also be improved by making dependencies such as user input explicitly injectable rather than binding them as default arguments.

### Future Enhancements

Future versions could add spaced repetition, persistent learning history, and richer reporting using the existing strategy architecture.

## Conclusion

The Flashcard Quizzer satisfies the project's functional and architectural requirements while demonstrating a disciplined AI-assisted engineering workflow. The final system combines modular Python design, extensible quiz strategies, robust validation, CLI interaction, comprehensive testing, and automated quality controls.

More importantly, the project demonstrated that AI-generated code still requires engineering ownership. Prompting accelerated implementation, but reviewing assumptions, identifying failures, refining behavior, and independently verifying quality were essential to achieving the final result.

## Appendices

### Appendix A: AI Interaction Log

Detailed interaction records are maintained in docs/ai_edit_log.md, including the initial architecture work, validation development, adaptive-mode refinement, testing issues, and final verification.

### Appendix B: Code Quality Results

- Tests: 208 passed, 0 failed
- Coverage: 99%
- flake8: 0 errors
- Required coverage threshold: greater than 80%

