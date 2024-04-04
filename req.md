## AI4Help

### service1

create a service to start a session. you will get the context labels from frontend. 
payload
```JSON
{
"topics": {"python","large data","python packages","devops","aws","ide vscode","ai"}
}
```

#### response
```JSON
{
"msg":"success"
}
```

now that the context is set we start the session for conversation
payload
```JSON
{
"q":"what pacakage is needed to process large data"
}
```

respose
```JSON
{
//streem response from gpt
}
```
as the streeming is happening save the 'q' and response in mongodb along with the labels

sample document in mongodb
```JSON
{
"topics": {"python","large data","python packages","devops","aws","ide vscode","ai"},
"conversation":{{
"q":"what pacakage is needed to process large data",
"resp":""
},
{
"q":"what pacakage is needed to process large data",
"resp":""
},
}
}
```


### Service 2

receive a *document* (docx or pdf)

read the doc and create topics. will update this as we go
