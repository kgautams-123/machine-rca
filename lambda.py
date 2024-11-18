import json
import boto3
import re
import json
import time

bedrock_runtime = boto3.client(
    service_name='bedrock-runtime',
    region_name='us-east-1'
)

def lambda_handler(event, context):
    
    response_body = {}
    print(event)
    input_text = event['inputText']
    api_path=event['apiPath']
    if api_path == '/generate_query_and_get_data_from_redshift':
        modelId = "anthropic.claude-3-sonnet-20240229-v1:0"
        accept = "application/json"
        contentType = "application/json"
        temperature = 0.1
        
        # Updated request body format for Claude 3
        response = bedrock_runtime.invoke_model(
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt_template.format(question=input_text)
                    }
                ],
                "max_tokens": 10000,
                "temperature": temperature
            }),
            modelId=modelId,
            accept=accept,
            contentType=contentType
        )

        response_content = response['body'].read().decode('utf-8')
        answer = json.loads(response_content).get('content')[0].get('text')
        query_match=re.findall('<Query>'+"(.*)"+'</Query>',answer, flags=re.DOTALL | re.MULTILINE)
        print(answer)
        if query_match:
            sql = query_match[0].replace("```", '')
        else:
            # Handle the case when no match is found
            sql = answer
        print(sql)
        client = boto3.client('redshift-data',region_name="us-east-1")
        response = client.execute_statement(
            ClusterIdentifier='abc-demo',
            Database='dev',
            Sql=sql,
            SecretArn='xyz',
            
        )
        # Wait for the query to complete
        time.sleep(10)
        print(response)
        records=client.get_statement_result(Id=response["Id"])["Records"]
        print(records)
        #print(records)
        final_prompt=prompt_explanation.format(question=input_text,query=answer,records=records)
        #print(final_prompt)
        # Updated explanation request for Claude 3
        explanation = bedrock_runtime.invoke_model(
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "messages": [
                    {
                        "role": "user",
                        "content": final_prompt
                    }
                ],
                "max_tokens": 10000,
                "temperature": temperature
            }),
            modelId=modelId,
            accept=accept,
            contentType=contentType
        )
        
        answer = json.loads(explanation.get('body').read()).get('content').get('text')
        
        script_prompt = prompt_charting.format(question=input_text, query=answer, records=records, explanation=answer)
        
        # Updated script request for Claude 3
        script = bedrock_runtime.invoke_model(
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "messages": [
                    {
                        "role": "user",
                        "content": script_prompt
                    }
                ],
                "max_tokens": 10000,
                "temperature": temperature
            }),
            modelId=modelId,
            accept=accept,
            contentType=contentType
        )
        
        script = json.loads(script.get('body').read()).get('content').get('text')
        
        response_body = {
            'application/json': {
                'answer': answer,
                'script': script
            }
        }
        
        print(response_body)
        return response_body

        # # Using regex to extract text between <Response> and </Response> tags
        # match = re.search(r'<Response>(.*?)</Response>', answer, re.DOTALL | re.IGNORECASE)
        
        # if match:
        #     extracted_text = match.group(1).strip()
        #     full_text = extracted_text  # Convert to list
        # else:
        #     full_text = answer  # Convert to list
        
        # print(full_text)
        # return json.dumps(full_text)  # Serialize the list to JSON
        
        
prompt_template = """Human: Your goal converting complex business queries into simple and distinct subqueries.

<System>You will be acting as an AI Redshift SQL expert responsible for generating analytics for a manufacturing company. 
</System>

<Instructions>
    - Consider only one question do not ask further questions
    - Convert {{Question}} into an SQL query
    - Do not use an aggregate in the subquery
    - Give ONLY the SQL query followed by a semicolon as <Query>
    - If Conversation History is provided, always follow the chain of thoughts to give the <Query> 
</Instructions>
<Tables>
```yaml
- schema: sc_pcr_curing
  table: t_curing_batch
  columns:
    - name: id
    - name: sku_code
    - name: machine_number
    - name: dry_cycle_time
    - name: curing_time
    - name: month
    - name: year
    - name: cure_medium

- schema: sc_pcr_curing
  table: t_asset_master
  columns:
    - name: workcenter
    - name: machinesupplier
    - name: machinetype
```
</Tables>

<Calculations>
    {{dry_cycle_time}} = {{gt_loading_time}} + {{shaping_time}} + {{press_close_time}} + {{press_open_time}} + {{unloading_time}}

</Calculations>


<Gaurdrails>
	-If you are unable to form SQL query from the user question, just say 'Can you please rephrase your question'
	- Always stay in character of an AI Redshift SQL Analytics expert.
</Gaurdrails>

<SQLGuidelines>
	-Unless mentioned otherwise, limit the query output by using LIMIT 20 in the
query.
	- Before the table name add schema name .
	- Always return query without any explanation.
	- When dry cycle time or DCT is used in the {question}, generate SQL query to retrieve information from two tables in the sc_pcr_curing schema. The tables are t_curing_batch and t_asset_master.
	- When dry cycle time or DCT along with supplier HF and LT is used in the prompt query two tables join using machine_number in t_curing_batch and workcenter in t_asset_master.
	- When wet cycle time or WCT is used in the {question}, generate SQL query to retrieve information from two tables in the sc_pcr_curing schema. The tables are t_timeseries_data and t_asset_master.
	- When wet cycle time or WCT along with supplier HF and LT is used in the prompt query two tables join using machine_number in t_timeseries_data and workcenter in t_asset_master.
	- When supplier HF or LT is used append double quotes(") as HF" or LT".
	- When curing time is asked add dry cycle time and wet cycle time.
	- Remove semicolon at the end from SQL query.
  - When asked for the highest or lowest, retrieve the top 3 records accordingly.
	
</SQLGuidelines>

<Examples>
  - Question: Which SKU has got the highest dry cycle time for last month for 52 inch machine type and HF supplier?
    Answer: 
      <Query>
        SELECT tcb.sku_code, (tcb.dry_cycle_time) FROM sc_pcr_curing.t_curing_batch tcb JOIN sc_pcr_curing.t_asset_master am ON tcb.machine_number = am.workcenter 
        WHERE tcb.machine_number LIKE 'P1007%' AND tcb.month = EXTRACT(MONTH FROM CURRENT_DATE - INTERVAL '1' MONTH) AND 
        tcb.year = EXTRACT(YEAR FROM CURRENT_DATE) AND am.machinesupplier = 'HF' and machinetype ='52"' GROUP BY tcb.sku_code ORDER BY tcb.dry_cycle_time desc LIMIT 5"
      </Query>
  - Question: Which SKU has the highest dry cycle time for last month for cure medium as steam and machine supplier as HF?
    Answer: 
      <Query>
        SELECT tcb.sku_code, (tcb.dry_cycle_time) FROM sc_pcr_curing.t_curing_batch tcb JOIN sc_pcr_curing.t_asset_master am ON tcb.machine_number = am.workcenter 
        WHERE tcb.month = EXTRACT(MONTH FROM CURRENT_DATE - INTERVAL '1' MONTH) AND 
        tcb.year = EXTRACT(YEAR FROM CURRENT_DATE) AND am.machinesupplier = 'HF' AND tcb.cure_medium = '0'  GROUP BY tcb.sku_code ORDER BY tcb.dry_cycle_time desc LIMIT 5"
      </Query>
      
  
      
    - Question: Which SKU has got the highest curing cycle time in Feb 2024?
    Answer: 
      <Query>
        SELECT tcb.sku_code, (tcb.dry_cycle_time + tcb.curing_time) AS total_time
        FROM sc_pcr_curing.t_curing_batch tcb 
        JOIN sc_pcr_curing.t_asset_master am ON tcb.machine_number = am.workcenter
        WHERE  tcb.month = 2 AND tcb.year = 2024
        GROUP BY tcb.sku_code 
        ORDER BY total_time DESC
        LIMIT 5
      </Query>


</Examples>


Question:{question}

Assistant:

"""

prompt_explanation="""
Human:
Your goal converting complex business queries into simple explanation supported by Reference Data.

<System>You will be acting as an AI Analyst responsible for generating analytics for manufacturing company. 
</System>

<Instructions>
	- Give Response in <Response> tag of {{Question}} in simple plain english based on <Query> and <Records> in prompt
	- Also Give evidence based on data available in <Records> but do not expose <Query> and <Records> in Response
	- If sufficient data is not avaialble to answer {{Question}} only then ask further question from user in <Agent> tag in Response
	- If <ConversationHistory> is provided, always follow the chain of thoughts to give the <Query>
  - Do not generate any synthetic or imaginary or sample data for analytics, if data is not available then ask further question
  - Always give response as bullet points mentioning only the key details highlited in bold whereever necessary.
</Instructions>


<Calculations>
	-{{dry_cycle_time}} = {{gt_loading_time}} + {{shaping_time}} +  {{press_close_time}}  + {{press_open_time}} + {{unloading_time}}

</Calculations>

<Gaurdrails>
	-If you are unable to form response from the user question, just say 'Can you please rephrase your question
	- Always stay in character of an AI Analytics expert.
</Gaurdrails>

<ResponseFormat>
```
Answer:
Evidence:
```
</ResponseFormat>

<Examples>
```yaml
```
</Examples>

<ConversationHistory>
```yaml
```
</ConversationHistory>

<Query>
{query}
</Query>
<Records>
{records}
</Records>
Question:{question}

Assistant:

"""

prompt_charting="""
Human:
Your goal converting complex business queries into simple Chart supported by Reference Data.

<System>You will be acting as an AI Analyst responsible for generating Chart script using Plotly library 
</System>

<Instructions>
    - Give Response in <Script> tag for {{Question}} in simple Chart based on <Query> and <Records> in prompt
    - Chart Should Explain reasoning behind <Explanation> based on data available in <Records>
    - Best Chart of <ChartTypes> should be selected based on question and explanation 
    - Generate a Title for chart based on <Explanation> for {{Question}}
    - Do not Generate any data which is not in <Records>
    - If there no data in <Records> then do not generate chart script
    - Always give plotly script which renders graph in white background
    - Always add st.plotly_chart(fig) in the generate chart script

    
    
</Instructions>

<ChartTypes>

  -Scatter Plot
  -Line Chart
  -Bar Chart
  -Pie Chart
  -Donut Chart

</ChartTypes>

<Calculations>
    -{{dry_cycle_time}} = {{gt_loading_time}} + {{shaping_time}} +  {{press_close_time}}  + {{press_open_time}} + {{unloading_time}}

</Calculations>

<Gaurdrails>
    - Always stay in character of an AI Analytics expert.
</Gaurdrails>

<ResponseFormat>
```javascript
<Script>
</script>

<Examples>
<BarChart>
labels = ["Italy", "France", "Spain", "USA", "Argentina"]
values = [55, 49, 44, 24, 15]
fig = go.Figure(data=[go.Bar(x=labels, y=values)])
fig.update_layout(title='Bar Chart', plot_bgcolor='rgb(51, 51, 51)', paper_bgcolor='rgb(51, 51, 51)', font=dict(color='white'))
</BarChart>

<Query>
{query}
</Query>
<Records>
{records}
</Records>
<Explanation>
{explanation}
</Explanation>
Question:Create a chart which will help to explain answer of following question-{question}

Assistant:

"""