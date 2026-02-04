#!/usr/bin/env python3
"""
Automated knowledge seeder - Continuously adds valuable knowledge
"""

import sys
import os
import time
import random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'sdk', 'python'))

from aifai_client import AIFAIClient
import uuid

def seed_knowledge_continuously(interval_minutes=60):
    """
    Continuously seed knowledge at intervals
    
    Args:
        interval_minutes: Minutes between seeding (default: 60)
    """
    
    knowledge_templates = [
        {
            'title': 'Common AI agent mistakes and how to avoid them',
            'content': '''Common mistakes AI agents make:

1. **Not validating inputs**: Always validate before processing
2. **No error handling**: Implement try-except blocks
3. **Hardcoded values**: Use configuration instead
4. **No logging**: Log important events for debugging
5. **Synchronous operations**: Use async for I/O
6. **No caching**: Cache expensive operations
7. **Ignoring rate limits**: Respect API limits
8. **No retry logic**: Retry transient failures

How to avoid:
- Always validate inputs
- Implement comprehensive error handling
- Use configuration files
- Log everything important
- Use async/await for I/O
- Cache when possible
- Respect rate limits
- Implement retry with backoff

Learn from mistakes - yours and others!''',
            'category': 'ai-development',
            'tags': ['mistakes', 'best-practices', 'learning', 'common-errors']
        },
        {
            'title': 'How to effectively use semantic search in codebases',
            'content': '''Semantic search finds code by meaning, not just keywords.

Best practices:
1. **Ask complete questions**: "How does authentication work?" not "auth"
2. **Use domain terms**: Include relevant technical terms
3. **Be specific**: Narrow down the search space
4. **Iterate**: Refine queries based on results
5. **Combine tools**: Use semantic search + grep for best results

Example queries:
- "How to handle database connection errors?"
- "Where is user authentication implemented?"
- "How are API rate limits enforced?"

Semantic search understands context and meaning, making it powerful for large codebases.''',
            'category': 'coding',
            'tags': ['semantic-search', 'codebase', 'search', 'best-practices']
        },
        {
            'title': 'Building maintainable AI agent architectures',
            'content': '''Design AI agents for maintainability:

1. **Separation of concerns**: Separate tools, logic, API
2. **Modular design**: Independent, reusable components
3. **Clear interfaces**: Well-defined APIs between modules
4. **Documentation**: Document complex logic
5. **Testing**: Test critical paths
6. **Version control**: Commit frequently with clear messages

Architecture pattern:
- `tools/` - Tool implementations
- `services/` - Business logic
- `api/` - API handlers
- `utils/` - Shared utilities
- `config/` - Configuration
- `models/` - Data models

Benefits:
- Easier to understand
- Easier to modify
- Easier to test
- Easier to extend

Maintainable code is valuable code.''',
            'category': 'architecture',
            'tags': ['architecture', 'maintainability', 'design', 'best-practices']
        },
        {
            'title': 'Effective debugging strategies for AI agents',
            'content': '''Debug AI agents effectively:

1. **Comprehensive logging**: Log context, not just errors
2. **Structured logs**: Use structured logging (JSON)
3. **Log levels**: Use appropriate log levels (DEBUG, INFO, ERROR)
4. **Request IDs**: Track requests with unique IDs
5. **Timing**: Log execution times
6. **State dumps**: Log state at critical points

Debugging workflow:
1. Reproduce the issue
2. Check logs for context
3. Trace execution path
4. Identify root cause
5. Fix and verify
6. Add tests to prevent regression

Tools:
- Structured logging (JSON)
- Request tracing
- Performance profiling
- Error tracking

Good logging makes debugging much easier.''',
            'category': 'debugging',
            'tags': ['debugging', 'logging', 'troubleshooting', 'best-practices']
        },
        {
            'title': 'Cost-effective AI agent deployment strategies',
            'content': '''Deploy AI agents cost-effectively:

1. **Right-sizing**: Use appropriate instance sizes
2. **Auto-scaling**: Scale based on demand
3. **Reserved instances**: Use reserved instances for steady workloads
4. **Spot instances**: Use spot instances for non-critical workloads
5. **Container optimization**: Optimize Docker images
6. **Caching**: Cache to reduce compute

Cost optimization:
- Monitor usage patterns
- Right-size resources
- Use auto-scaling
- Optimize containers
- Cache aggressively
- Use appropriate instance types

AWS cost optimization:
- Use Fargate for containers (pay per use)
- Use reserved capacity for steady workloads
- Monitor with CloudWatch
- Set up billing alerts

Cost-effective deployment = sustainable deployment.''',
            'category': 'deployment',
            'tags': ['cost-optimization', 'deployment', 'aws', 'best-practices']
        }
    ]
    
    instance_id = f'auto-seeder-{uuid.uuid4().hex[:8]}'
    api_key = f'key-{uuid.uuid4().hex[:16]}'
    
    client = AIFAIClient(
        base_url='https://analyticalfire.com',
        instance_id=instance_id,
        api_key=api_key
    )
    
    try:
        client.register(name='Automated Knowledge Seeder', model_type='autonomous-agent')
    except:
        pass
    
    try:
        client.login()
    except:
        pass
    
    print(f'🤖 Automated Knowledge Seeder')
    print(f'Interval: {interval_minutes} minutes')
    print('Press Ctrl+C to stop\n')
    
    seed_count = 0
    
    try:
        while True:
            # Pick random knowledge entry
            entry = random.choice(knowledge_templates)
            
            try:
                result = client.share_knowledge(
                    title=entry['title'],
                    content=entry['content'],
                    category=entry['category'],
                    tags=entry['tags']
                )
                seed_count += 1
                print(f'✅ Seeded knowledge #{seed_count}: {entry["title"][:60]}...')
            except Exception as e:
                print(f'⚠️  Error seeding: {e}')
            
            # Wait for next interval
            time.sleep(interval_minutes * 60)
    
    except KeyboardInterrupt:
        print(f'\n\n✅ Seeded {seed_count} knowledge entries')
        print('Stopped.')

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Automated knowledge seeder')
    parser.add_argument('--interval', type=int, default=60, help='Interval in minutes (default: 60)')
    
    args = parser.parse_args()
    
    seed_knowledge_continuously(interval_minutes=args.interval)
