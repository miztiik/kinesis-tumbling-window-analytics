# Streaming Analytics Using Kinesis Data Analytics

The executives at Mystique Unicorn are interested in getting near real-time insights into the sales performance of their stores. They are mutliple stores in multiple locations. All of these stores send their sales records as a stream of events to a kinesis data stream at regular intervals throughout the day. They would like to have a real-time dashboard that shows them the sales revenue per store. In future they would like to expand this capability to drill down to find out which category is most popular. For example, A typical question that often gets asked is, Which category did we sell more today? _Electronics_ or _Books_? 

They heard that AWS offers analytics capabilities on streaming events of data. Can you help them?


## 🎯 Solutions

AWS offers multiple capabilities to peform analytics on streaming data. As they are using kinesis data streams to ingest the stream of sales events, We can leverage Kinesis Data Analytics capability with AWS to perform stream analytics using regular `SQL` or `Apache Flink`. In this solution, we will use simple SQL query to calculate the `revenue_per_store` metric and store the value in S3 for further processing.

![Miztiik Automation: Streaming Analytics Using Kinesis Data Analytics](images/miztiik_automation_kinesis_tumbling_window_analytics_architecture_03.png)

The incoming data event payload looks something like this.

```json
{
  "category": "Electronics",
  "store_id": "store_3",
  "evnt_time": "2021-01-31T14:05:47.190114",
  "sales": 22.78
}
```

We will use the `store_id` to summarize the `sales` and calculate the `revenue` of that store for a given period of time. Let us assume, we want to calculate the revenue of each store `per_minute`. At this point we will have a stream revnenue events from kinesis analytics(KDA). We can use either data stream or firehose depending upon the downstream consumers. 

![Miztiik Automation: Streaming Analytics Using Kinesis Data Analytics](images/miztiik_automation_kinesis_tumbling_window_analytics_architecture_04.png)

In this example, I am going to be using Kinesis firehose to store the events in S3. Before ingesting the revenue records in S3, I am going to use a lambda function to do some basic transformation like adding a _new line_ character between each record coming from KDA. This will help data processing in the future using Redshift/Athena.

The final AWS architecture looks something like,
![Miztiik Automation: Streaming Analytics Using Kinesis Data Analytics](images/miztiik_automation_kinesis_tumbling_window_analytics_architecture_00.png)

In this article, we will build an architecture, similar to the one shown above. We will start backwards so that all the dependencies are satisfied.

1.  ## 🧰 Prerequisites

    This demo, instructions, scripts and cloudformation template is designed to be run in `us-east-1`. With few modifications you can try it out in other regions as well(_Not covered here_).

    - 🛠 AWS CLI Installed & Configured - [Get help here](https://youtu.be/TPyyfmQte0U)
    - 🛠 AWS CDK Installed & Configured - [Get help here](https://www.youtube.com/watch?v=MKwxpszw0Rc)
    - 🛠 Python Packages, _Change the below commands to suit your OS, the following is written for amzn linux 2_
      - Python3 - `yum install -y python3`
      - Python Pip - `yum install -y python-pip`
      - Virtualenv - `pip3 install virtualenv`

1.  ## ⚙️ Setting up the environment

    - Get the application code

      ```bash
      git clone https://github.com/miztiik/kinesis-tumbling-window-analytics
      cd kinesis-tumbling-window-analytics
      ```

1.  ## 🚀 Prepare the dev environment to run AWS CDK

    We will use `cdk` to make our deployments easier. Lets go ahead and install the necessary components.

    ```bash
    # You should have npm pre-installed
    # If you DONT have cdk installed
    npm install -g aws-cdk

    # Make sure you in root directory
    python3 -m venv .venv
    source .venv/bin/activate
    pip3 install -r requirements.txt
    ```

    The very first time you deploy an AWS CDK app into an environment _(account/region)_, you’ll need to install a `bootstrap stack`, Otherwise just go ahead and deploy using `cdk deploy`.

    ```bash
    cdk bootstrap
    cdk ls
    # Follow on screen prompts
    ```

    You should see an output of the available stacks,

    ```bash
    kinesis-tumbling-window-analytics-producer-stack
    kinesis-tumbling-window-analytics-firehose-stack
    kinesis-tumbling-window-analytics-consumer-stack
    ```

1.  ## 🚀 Deploying the application

    Let us walk through each of the stacks,

    - **Stack: kinesis-tumbling-window-analytics-producer-stack**

      This stack will create a kinesis data stream and the producer lambda function. Each lambda runs for a minute ingesting stream of sales events for `5` different stores ranging from `store_id=1` to `store_id=5`

      Initiate the deployment with the following command,

      ```bash
      cdk deploy kinesis-tumbling-window-analytics-producer-stack
      ```

      After successfully deploying the stack, Check the `Outputs` section of the stack. You will find the `streamDataProcessor` producer lambda function. We will invoke this function later during our testing phase.

    - **Stack: kinesis-tumbling-window-analytics-firehose-stack**

      This stack will create the firehose stack to receive the stream of events from kinesis analytics and also deploy the simple lambda transformer. This firehose is set to buffer for `1` minute or until `1`MB of data is collected before sending it to S3

      Initiate the deployment with the following command,

      ```bash
      cdk deploy kinesis-tumbling-window-analytics-firehose-stack
      ```

      After successfully deploying the stack, Check the `Outputs` section of the stack. You will find the `FirehoseDataStore` where the analytics results will be stored eventually.

    - **Stack: kinesis-tumbling-window-analytics-consumer-stack**

      This stack will create the kinesis analytics. The SQL _application code_ that does the magic of aggregating sales across stores is baked into the stack. If you would like to take a look and make some improvments

      ```sql
      "CREATE OR REPLACE STREAM "DEST_SQL_STREAM_BY_STORE_ID" ("store_id" VARCHAR(16),"revenue" REAL, "timestamp" TIMESTAMP);
        CREATE OR REPLACE PUMP "STREAM_PUMP" AS INSERT INTO "DEST_SQL_STREAM_BY_STORE_ID"
            SELECT STREAM "store_id", SUM("sales") AS "revenue", ROWTIME AS "timestamp"
                FROM "STORE_REVENUE_PER_MIN_001"
                GROUP BY STEP("STORE_REVENUE_PER_MIN_001".ROWTIME BY INTERVAL '60' SECOND),
                "store_id";
      ```
      Here we are aggregating the sales revenue per store per minute. Initiate the deployment with the following command,

      ```bash
      cdk deploy kinesis-tumbling-window-analytics-consumer-stack
      ```

1.  ## 🔬 Testing the solution

    Before we go ahead and start testing the solution, We need to start the Kinesis Analytics Application. Unfortunately(or maybe fortunately for cost reasons) we cannot start it automatically through cloudformation. We will have to do it through a custom resource(which is initself a pain to maintain) or do it manually. 
    
    1. **Start Kinesis Analytics Application**:
      Here is a screenshot, to help you do that. Navigate to kineis analytics and choose `Run`.
      ![Miztiik Automation: Streaming Analytics Using Kinesis Data Analytics](images/miztiik_automation_kinesis_tumbling_window_analytics_architecture_06.png)
    1. **Invoke Producer Lambda**:
      Let us start by invoking the lambda from the producer stack `kinesis-tumbling-window-analytics-producer-stack` using the AWS Console. If you want to ingest more events, use another browser window and invoke the lambda again.
          ```json
          {
            "statusCode": 200,
            "body": "{\"message\": {\"status\": true, \"record_count\": 1170, \"tot_sales\": 59109.60999999987}}"
          }
          ```
        Here in this invocation, I have ingested about `1170` events and the total sales volume across all stores`[1..5]` is `59109`.
    1. **Check FirehoseDataStore**:

       After about `60` seconds, Navigate to the data store S3 Bucket created by the firehose stack `kinesis-tumbling-window-analytics-firehose-stack`. You will be able to find an object key similar to this `kinesis-tumbling-window-analy-fhdatastore6289deb2-5iydp3790az3sales_revenue/2021/01/31/14/revenue_analytics_stream-1-2021-01-31-14-11-00-b2412476-aace-41a7-bbd5-e1a170d2573c`. 

       Kinesis firehose does not have a native mechanism to set the file extension. I was not too keen on setting up another lambda to add the suffix. But the file contents should be one valid `JSON` object per line.

      The contents of the file should look like this, 
      ```json
      {"store_id": "store_1", "revenue": 8671.3125, "timestamp": "2021-01-31 14:47:00.000"}
      {"store_id": "store_4", "revenue": 10318.991, "timestamp": "2021-01-31 14:47:00.000"}
      {"store_id": "store_5", "revenue": 8561.629, "timestamp": "2021-01-31 14:47:00.000"}
      {"store_id": "store_3", "revenue": 9370.749, "timestamp": "2021-01-31 14:47:00.000"}
      {"store_id": "store_2", "revenue": 8606.821, "timestamp": "2021-01-31 14:47:00.000"}

      ```

      You can observe that the revenue per store is aggregated and stored along with `store_id` and `timestamp` attribute. You can feed this into a dashboard like kibana for the executives to provide a real-time snapshot of the sales happening in the stores.


1.  ## 📒 Conclusion

    Here we have demonstrated how to use kinesis analytics using simple SQL queries for performing steaming analytics on incoming data. You can extend this further by enriching the item before storing in S3 or partitioning it better for ingesting into data lake platforms.

1.  ## 🧹 CleanUp

    If you want to destroy all the resources created by the stack, Execute the below command to delete the stack, or _you can delete the stack from console as well_

    - Resources created during [Deploying The Application](#-deploying-the-application)
    - Delete CloudWatch Lambda LogGroups
    - _Any other custom resources, you have created for this demo_

    ```bash
    # Delete from cdk
    cdk destroy

    # Follow any on-screen prompts

    # Delete the CF Stack, If you used cloudformation to deploy the stack.
    aws cloudformation delete-stack \
      --stack-name "MiztiikAutomationStack" \
      --region "${AWS_REGION}"
    ```

    This is not an exhaustive list, please carry out other necessary steps as maybe applicable to your needs.

## 📌 Who is using this

This repository aims to show how to perform streaming analtics to new developers, Solution Architects & Ops Engineers in AWS. Based on that knowledge these Udemy [course #1][103], [course #2][102] helps you build complete architecture in AWS.

### 💡 Help/Suggestions or 🐛 Bugs

Thank you for your interest in contributing to our project. Whether it is a bug report, new feature, correction, or additional documentation or solutions, we greatly value feedback and contributions from our community. [Start here](/issues)

### 👋 Buy me a coffee

[![ko-fi](https://www.ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/Q5Q41QDGK) Buy me a [coffee ☕][900].

### 📚 References

1. [Docs: Kinesis Analytics Tumbling Windows - Flink][1]

1. [Docs: Kinesis Streaming Analytics - GROUP BY][2]

1. [Docs: Tumbling Window Using an Event Timestamp][3]

1. [Blog: Kinesis Firehose S3 Custom Prefix][4]

1. [Docs: Kinesis Firehose S3 Custom Prefix][5]

1. [Docs: Kinesis Analytics IAM Role][6]


### 🏷️ Metadata

![miztiik-success-green](https://img.shields.io/badge/Miztiik:Automation:Level-300-blue)

**Level**: 300

[1]: https://docs.aws.amazon.com/kinesisanalytics/latest/java/examples-tumbling.html
[2]: https://docs.aws.amazon.com/kinesisanalytics/latest/dev/tumbling-window-concepts.html
[3]: https://docs.aws.amazon.com/kinesisanalytics/latest/dev/examples-window-tumbling-event.html
[4]: https://aws.amazon.com/blogs/big-data/amazon-kinesis-data-firehose-custom-prefixes-for-amazon-s3-objects/
[5]: https://docs.aws.amazon.com/firehose/latest/dev/s3-prefixes.html
[6]: https://docs.aws.amazon.com/kinesisanalytics/latest/dev/iam-role.html#iam-role-trust-policy

[100]: https://www.udemy.com/course/aws-cloud-security/?referralCode=B7F1B6C78B45ADAF77A9
[101]: https://www.udemy.com/course/aws-cloud-security-proactive-way/?referralCode=71DC542AD4481309A441
[102]: https://www.udemy.com/course/aws-cloud-development-kit-from-beginner-to-professional/?referralCode=E15D7FB64E417C547579
[103]: https://www.udemy.com/course/aws-cloudformation-basics?referralCode=93AD3B1530BC871093D6
[899]: https://www.udemy.com/user/n-kumar/
[900]: https://ko-fi.com/miztiik
[901]: https://ko-fi.com/Q5Q41QDGK
