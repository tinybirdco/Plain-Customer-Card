import json
import logging
import urllib.parse
import boto3
import requests
from typing import Dict, Any, List

logger = logging.getLogger()
logger.setLevel(logging.INFO)


secretsmanager = boto3.client('secretsmanager')
TINYBIRD_SECRET_NAME = 'plain-customer-card-tb-token'
TINYBIRD_ENDPOINT = 'https://api.europe-west2.gcp.tinybird.co/v0/pipes/plain_customer_card_lookup.json'


def get_tinybird_token() -> str:
    try:
        logger.info(f"Fetching secret: {TINYBIRD_SECRET_NAME}")
        response = secretsmanager.get_secret_value(SecretId=TINYBIRD_SECRET_NAME)
        secret = json.loads(response['SecretString'])
        token = secret[TINYBIRD_SECRET_NAME]
        logger.info("Successfully retrieved Tinybird token")
        return token
    except Exception as e:
        logger.error(f"Failed to retrieve Tinybird token: {str(e)}")
        raise Exception(f"Failed to retrieve Tinybird token: {str(e)}")


def fetch_customer_data(email: str, token: str) -> Dict[str, Any]:
    try:
        logger.info(f"Fetching customer data for email: {email}")
        params = {
            'user_email': email,
            'token': token
        }
        response = requests.get(TINYBIRD_ENDPOINT, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        logger.info(f"Tinybird response - rows: {data.get('rows', 0)}, data items: {len(data.get('data', []))}")
        logger.debug(f"Full Tinybird response: {json.dumps(data)}")
        return data
    except requests.RequestException as e:
        logger.error(f"Failed to fetch data from Tinybird: {str(e)}")
        raise Exception(f"Failed to fetch data from Tinybird: {str(e)}")


def build_plain_response(tinybird_data: Dict[str, Any]) -> Dict[str, Any]:
    if not tinybird_data.get('data') or len(tinybird_data['data']) == 0:
        logger.warning("No customer data found in Tinybird response")
        return {
            "cards": [{
                "key": "customer-info",
                "timeToLiveSeconds": 86400,
                "components": [{
                    "componentText": {
                        "text": "No customer data found",
                        "textColor": "MUTED"
                    }
                }]
            }]
        }
    
    customer = tinybird_data['data'][0]
    logger.info(f"Building Plain response for customer: {customer.get('organization_name', 'N/A')}")
    
    is_dedicated = customer.get('dedicated_clusters_url', '').lower() == 'yes'
    
    return {
        "cards": [{
            "key": "customer-info",
            "timeToLiveSeconds": 86400,
            "components": [{
                "componentContainer": {
                    "containerContent": [
                        {
                            "componentRow": {
                                "rowMainContent": [
                                    {
                                        "componentText": {
                                            "text": customer.get('organization_name', 'N/A')
                                        }
                                    },
                                    {
                                        "componentText": {
                                            "text": customer.get('plan_name', 'N/A'),
                                            "textColor": "MUTED"
                                        }
                                    }
                                ],
                                "rowAsideContent": [
                                    {
                                        "componentLinkButton": {
                                            "linkButtonLabel": "Organization ↗",
                                            "linkButtonUrl": customer.get('organization_url', '#')
                                        }
                                    }
                                ]
                            }
                        },
                        {
                            "componentDivider": {
                                "dividerSpacingSize": "M"
                            }
                        },
                        {
                            "componentRow": {
                                "rowMainContent": [
                                    {
                                        "componentText": {
                                            "text": "Region",
                                            "textSize": "S",
                                            "textColor": "MUTED"
                                        }
                                    },
                                    {
                                        "componentText": {
                                            "text": customer.get('region', 'N/A')
                                        }
                                    }
                                ],
                                "rowAsideContent": [
                                    {
                                        "componentBadge": {
                                            "badgeLabel": f"Dedicated cluster: {'YES' if is_dedicated else 'NO'}",
                                            "badgeColor": "GREEN" if is_dedicated else "RED"
                                        }
                                    }
                                ]
                            }
                        },
                        {
                            "componentSpacer": {
                                "spacerSize": "M"
                            }
                        },
                        {
                            "componentRow": {
                                "rowMainContent": [
                                    {
                                        "componentText": {
                                            "text": "Customer created at",
                                            "textSize": "S",
                                            "textColor": "MUTED"
                                        }
                                    },
                                    {
                                        "componentText": {
                                            "text": customer.get('customer_created_at', 'N/A')
                                        }
                                    }
                                ],
                                "rowAsideContent": [
                                    {
                                        "componentText": {
                                            "text": "Contract duration (months)",
                                            "textSize": "S",
                                            "textColor": "MUTED"
                                        }
                                    },
                                    {
                                        "componentText": {
                                            "text": customer.get('current_contract_duration_in_months', 'N/A')
                                        }
                                    }
                                ]
                            }
                        },
                        {
                            "componentSpacer": {
                                "spacerSize": "M"
                            }
                        },
                        {
                            "componentRow": {
                                "rowMainContent": [
                                    {
                                        "componentText": {
                                            "text": "Active orgs",
                                            "textSize": "S",
                                            "textColor": "MUTED"
                                        }
                                    },
                                    {
                                        "componentText": {
                                            "text": customer.get('active_orgs', 'N/A') or 'N/A'
                                        }
                                    }
                                ],
                                "rowAsideContent": []
                            }
                        }
                    ]
                }
            }]
        }]
    }


def lambda_handler(event, context):
    try:
        logger.info("=== Lambda invocation started ===")
        logger.info(f"Raw event: {json.dumps(event)}")
        
        if 'body' in event:
            logger.info("Event has 'body' key, parsing as Function URL request")
            body = json.loads(event['body'])
        else:
            logger.info("Event has no 'body' key, using event directly")
            body = event
        
        logger.info(f"Parsed body: {json.dumps(body)}")
        
        customer_email = body.get('customer', {}).get('email')
        if not customer_email:
            logger.error(f"No email found. Customer object: {body.get('customer', {})}")
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Customer email not found in payload'})
            }
        
        logger.info(f"Extracted customer email: {customer_email}")
        
        token = get_tinybird_token()
        
        tinybird_data = fetch_customer_data(customer_email, token)
        
        plain_response = build_plain_response(tinybird_data)
        
        logger.info("Successfully generated Plain response")
        logger.debug(f"Plain response: {json.dumps(plain_response)}")
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps(plain_response)
        }
        
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
