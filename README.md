This explains how the customer info data populates in Plain tickets 

[Plain documentation](https://www.plain.com/docs/customer-cards#customer-cards)


1. Go to Plain > Settings > Customer Cards
2. Click Customer Info card
3. The URL is the ARN of an AWS lambda function (lambda_function.py)
4. Go to AWS development > CloudFormation (select eu-central-1 region) > [plain-customer-card-1](https://1.     1. <https://eu-central-1.console.aws.amazon.com/cloudformation/home?region=eu-central-1#/stacks/stackinfo?filteringText=&filteringStatus=active&viewNested=true&stackId=arn%3Aaws%3Acloudformation%3Aeu-central-1%3A819314934727%3Astack%2Fplain-customer-card-1%2Fb3c3bd10-a57d-11f0-a4d4-06bc1b2e9c83>)
5. Go to Resources tab > PlainCustomerCardFunction
6. lambda_function.py is the script that calls the Tinybird endpoint with the user_email and returns the output data in Plain customer card format.
7. The Function URL of the AWS lambda function matches the URL in the Plain Customer Card
8. The tinybird endpoint is in oa-sot-fwd workspace > endpoints > [plain-customer-card-lookup](https://cloud.tinybird.co/gcp/europe-west2/oa_sot_fwd/endpoints/plain_customer_card_lookup). It takes in user_email as a parameter. 
