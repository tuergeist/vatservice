# How to deploy to Elastic Beanstalk

* have your AWS account set up properly (updated `~/.aws/credentails` file)

```bash
eb init -p python-3.7 vatservice --region eu-west-1
eb create vatservice-env
eb open
```

## Logging
 
### Simple
* logfiles? see [eb logs help](https://docs.aws.amazon.com/de_de/elasticbeanstalk/latest/dg/eb3-logs.html)

`eb logs` for the last 100 lines, or
`eb logs --all` for all files 

### Cloudwatch

* you need to enable it upfront, if not yet done: `eb logs --cloudwatch-logs enable `
* then you'll get a URL like `https://console.aws.amazon.com/cloudwatch/home?region=eu-central-1#logs:prefix=/aws/elasticbeanstalk/vatservice/`
* or go to AWS Management Console, Cloudwatch, Log groups, search for '/aws/elasticbeanstalk/vatservice'
* in `var/log/web.stdout.log` the Python output can be found 



## Update the app

* Make sure you're in the git repo
* all goes via `eb deploy` - [help](https://docs.aws.amazon.com/de_de/elasticbeanstalk/latest/dg/eb3-deploy.html)
* If you want to deploy whats in the repo, run `eb deploy`
* If you want to deploy changes not in HEAD, run `eb deploy --staged`

