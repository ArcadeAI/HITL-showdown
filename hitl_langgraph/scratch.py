StateSnapshot(
    values={
        'messages': [
            HumanMessage(
                content='summarize my latest email',
                additional_kwargs={},
                response_metadata={},
                id='97312b5e-4f1a-45cb-9a82-1b3be97c991e'),
            AIMessage(
                content='',
                additional_kwargs={
                    'tool_calls': [
                        {
                            'id': 'call_WwJ9CljclAu7l WKN1KWEz9W2',
                            'function': {
                                'arguments': '{"n_emails":1}',
                                'name': 'Google_ListEmails'},
                            'type': 'function'
                        }
                    ],
                    'refusal': None
                },
                response_metadata={
                    'token_usage': {
                        'completion_tokens': 17,
                        'prompt_tokens': 4456,
                        'total_tokens': 4473,
                        'completion_tokens_det ails': {
                            'accepted_prediction_tokens': 0,
                            'audio_tokens': 0,
                            'reasoning_tokens': 0,
                            'rejected_prediction_tokens': 0
                        },
                        'prompt_tokens_details': {
                            'audio_tokens': 0,
                            'cached_tokens': 4352
                        }
                    },
                    'model_name': 'gpt-4o-2024-08-06',
                    'system_fingerprint': 'fp_55d88aa f2f',
                    'id': 'chatcmpl-Ba9Y8oBL6aIcYTpXsJUMLXwyzTcQ6',
                    'service_tier': 'default',
                    'finish_reason': 'tool_calls',
                    'logprobs': None
                },
                id='run--8caec8e6-2397-4f92-9d52-d571e923c1b5-0',
                tool_calls=[
                    {
                        'name': 'Google_ListEmails',
                        'args': {'n_emails': 1},
                        'id': ' call_WwJ9CljclAu7lWKN1KWEz9W2',
                        'type': 'tool_call'
                    }
                ],
                usage_metadata={
                    'input_tokens': 4456,
                    'output_tokens': 17,
                    'total_tokens': 4473,
                    'input_token_details': {
                        'audio': 0,
                        'cache_read': 4352
                    },
                    'output_token_details': {
                        'audio': 0,
                        'reasoning': 0
                    }
                })
        ]
    },
    next = ('tools',),
    config = {
        'configurable': {
            'thread_id': '4',
            'checkpoint_ns': '',
            'checkpoint_id': '1f03763c-9d2a-6a5e-8002-8bd72b4f6b13'
        }
    },
    metadata={
        'source': 'loop',
        'writes': {
            'authorization': {
                'messages': []
            }
        },
        'step': 2,
        'parents': {},
        'thread_id': '4',
        'user_id': 'mateo@arcade.dev'
    },
    created_at='2025-05-22T23:23:37.580176+00:00',
    parent_config={
        'configurable': {
            'thread_id': '4',
            'checkpoint_ns': '',
            'checkpoint_id': '1f03763c-9936-6bfa-8001-3ed8f9ef1b9c'
        }
    },
    tasks=(
        PregelTask(
            id='e8cd7295-fa1e-6643-3933- 0ff18fac0450',
            name='tools',
            path=('__pregel_pull', 'tools'),
            error=None,
            interrupts=(
                Interrupt(
                    value=[
                        {
                            'action_request': {
                                'action': 'Google_ListEmails',
                                'args': {'n_emails': 1}
                            },
                            'config': {
                                'allow_accept': True,
                                'allow_edit': True,
                                'allow_respond': True
                            },
                            'description': 'Please review the tool call'
                        }
                    ],
                    resumable=True,
                    ns=['tools:e8cd7295-fa1e-6643-3933-0ff18fac0450']
                ),
            ),
            state=None,
            result=None
        ),
    ),
    interrupts=(
        Interrupt(
            value=[
                {
                    'action_request': {
                        'action': 'Google_ListEmails',
                        'args': {'n_emails': 1}
                    },
                    'config': {
                        'allow_accept': True,
                        'allow_edit': True,
                        'allow_respond': True
                    },
                    'description': 'Please review the tool call'
                }
            ],
            resumable=True,
            ns=['tools:e8cd7295-fa1e-6643-3933-0ff18fac0450']),
        ))
