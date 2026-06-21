from services.tools.text_to_sql import TextToSQLTool
tool = TextToSQLTool()
result = tool.run({"query": "how many transactions went to the Uniswap V2 router?"})
print(result.output)