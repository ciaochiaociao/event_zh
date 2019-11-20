#!/bin/sh

set -e

#PROJECT_PATH=/workspace/EEtask/Chinese/event_zh/SinoCoreferencer
set -x
PROJECT_PATH=$EE_HOME/event_zh/SinoCoreferencer
set +x
#PROJECT_PATH="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
# STANFORD_CORENLP=$PROJECT_PATH/stanford-corenlp-full-2014-08-27
CRF=$PROJECT_PATH/CRF++-0.58
SVMMULTI=$PROJECT_PATH/svm_multiclass
MAXENT=$PROJECT_PATH/maxent/src/opt
SVMLIGHT=$PROJECT_PATH/svm_light
set -x
INPUTS=$1  # file that stores all filepaths to be extracted: test
set +x
EVPROPS=-Xmx2g

set -x
CURRENT_PATH=${PWD}  # .../workdir
set +x
# call stanford parser
echo "Call Stanford CoreNLP..."
# cd $STANFORD_CORENLP
# java -cp "*" -Xmx4g edu.stanford.nlp.pipeline.StanfordCoreNLP -props $CURRENT_PATH/chiPro -filelist $CURRENT_PATH/$INPUTS
while read -r line
do
	set -x
	name=$line  # filelist: .../SinoCoreferencer/data/doc, ...
	wget --post-file $name '140.109.19.190:9000/?properties={"outputFormat":"xml","annotators":"tokenize, ssplit, pos, ner, parse", "ssplit.boundaryTokenRegex": "[。]|[!?！？]+", "pipelineLanguage":"zh"}' -O - > $name.xml
	wget --post-file $name '140.109.19.190:9000/?properties={"outputFormat":"json","annotators":"tokenize, ssplit, pos, ner, parse", "ssplit.boundaryTokenRegex": "[。]|[!?！？]+", "pipelineLanguage":"zh"}' -O - > $name.json
    set +x
done < $CURRENT_PATH/$INPUTS  # read file .../SinoCoreferencer/test 

# echo "Move Stanford CoreNLP output..."  # to the directory of the file specified by $INPUTS
# while read -r line
# do
# 	set -x
# 	name=$line  # .../SinoCoreferencer/data/doc
# 	filename=${name##*/}  # doc
# 	set +x
# 	mv $STANFORD_CORENLP/$filename.xml $name.xml
# done < $CURRENT_PATH/$INPUTS

# run mention detection
echo "Run entity mention detection..."
cd $PROJECT_PATH
set -x
java $EVPROPS -cp $PROJECT_PATH/entity.jar MentionDetection/MentionDetectionEndToEnd $CURRENT_PATH/$INPUTS
set +x
cd $CRF
# test crf
while read -r line
do
	name=$line
	./crf_test -m $PROJECT_PATH/model/md.model $name.md.tmp > $name.md.crf

	# run time detection
	./crf_test -m $PROJECT_PATH/model/time.model $name.md.tmp > $name.time.crf

	# run value detection
	./crf_test -m $PROJECT_PATH/model/value.model $name.md.tmp > $name.value.crf
done < $CURRENT_PATH/$INPUTS


echo "Run entity typing & subtyping..."
# run entity typing & subtyping
cd $PROJECT_PATH
java $EVPROPS -cp $PROJECT_PATH/entity.jar SVMSemantic/EntitySemanticEndToEnd $CURRENT_PATH/$INPUTS 

cd $SVMMULTI
while read -r line
do
	name=$line
	./svm_multiclass_classify $name.type.svm $PROJECT_PATH/model/multiType.model $name.type.svmpred 1>&-
	./svm_multiclass_classify $name.type.svm $PROJECT_PATH/model/multiSubType.model $name.subtype.svmpred 1>&-
done < $CURRENT_PATH/$INPUTS

cd $PROJECT_PATH
java $EVPROPS -cp $PROJECT_PATH/entity.jar SVMSemantic/ExplainSemanticType $CURRENT_PATH/$INPUTS 1>&-



# run entity coreference
echo "Run entity coreference..."
cd $PROJECT_PATH
java $EVPROPS -cp $PROJECT_PATH/coref.jar ace/rule/RuleCoref $CURRENT_PATH/$INPUTS

echo "Run event trigger identification..."
# run event extraction
cd $PROJECT_PATH
java $EVPROPS -cp $PROJECT_PATH/event.jar event/trigger/JointTriggerEndToEnd $CURRENT_PATH/$INPUTS

cd $SVMMULTI
while read -r line
do
	name=$line
	./svm_multiclass_classify $name.trigger.svm $PROJECT_PATH/model/JointTriggerModel $name.trigger.svmpred 1>&-
done < $CURRENT_PATH/$INPUTS

cd $PROJECT_PATH

java $EVPROPS -cp $PROJECT_PATH/event.jar event/trigger/ExplainTrigger $CURRENT_PATH/$INPUTS

echo "Run event argument identification..."

java $EVPROPS -cp $PROJECT_PATH/event.jar event/argument/JointArgumentEndToEnd $CURRENT_PATH/$INPUTS

cd $SVMMULTI
while read -r line
do
	name=$line
	./svm_multiclass_classify $name.arg.svm $PROJECT_PATH/model/argumentJointModel $name.arg.svmpred 1>&-
done < $CURRENT_PATH/$INPUTS

cd $PROJECT_PATH
java $EVPROPS -cp $PROJECT_PATH/event.jar event/argument/ExplainArg $CURRENT_PATH/$INPUTS

echo "Run event attributes classification..."
# run event attribute classification
java $EVPROPS -cp $PROJECT_PATH/entity.jar event/attribute/EventAttriEndToEndTest tense $CURRENT_PATH/$INPUTS
java $EVPROPS -cp $PROJECT_PATH/entity.jar event/attribute/EventAttriEndToEndTest polarity $CURRENT_PATH/$INPUTS
java $EVPROPS -cp $PROJECT_PATH/entity.jar event/attribute/EventAttriEndToEndTest modality $CURRENT_PATH/$INPUTS
java $EVPROPS -cp $PROJECT_PATH/entity.jar event/attribute/EventAttriEndToEndTest genericity $CURRENT_PATH/$INPUTS

cd $MAXENT
while read -r line
do
	name=$line
	./maxent -p $name.polarity.fea -m $PROJECT_PATH/model/polarityModel --detail -o $name.polarity.pred 1>&-
	./maxent -p $name.modality.fea -m $PROJECT_PATH/model/modalityModel --detail -o $name.modality.pred 1>&-
	./maxent -p $name.genericity.fea -m $PROJECT_PATH/model/genericityModel --detail -o $name.genericity.pred 1>&-
	./maxent -p $name.tense.fea -m $PROJECT_PATH/model/tenseModel --detail -o $name.tense.pred 1>&-
done < $CURRENT_PATH/$INPUTS

cd $PROJECT_PATH
java $EVPROPS -cp $PROJECT_PATH/entity.jar event.attribute.ExplainAttribute $CURRENT_PATH/$INPUTS 

cd $PROJECT_PATH
echo "Run event coreference..."
# run event coreference
java $EVPROPS -cp $PROJECT_PATH/coref.jar ace/event/coref/MaxEntTestEnd2End $CURRENT_PATH/$INPUTS 1>&-

cd $SVMLIGHT
while read -r line
do
	name=$line
	./svm_classify $name.evc.svm $PROJECT_PATH/model/coref.model0 $name.evc.pred 1>&-
done < $CURRENT_PATH/$INPUTS

cd $PROJECT_PATH
java $EVPROPS -cp $PROJECT_PATH/coref.jar ace/event/coref/MakeCluster $CURRENT_PATH/$INPUTS 1>&-

echo "Cleaning..."
while read -r line
do
	name=$line
	rm $name.arg.svm
	rm $name.arg.svmpred
	rm $name.arg.tmp
	rm $name.evc.pred
	rm $name.evc.svm
	rm $name.genericity.fea
	rm $name.genericity.pred
	rm $name.md.tmp
	rm $name.modality.fea
	rm $name.modality.pred
	rm $name.polarity.fea
	rm $name.polarity.pred
	rm $name.subtype.svmpred
	rm $name.tense.fea
	rm $name.tense.pred
	rm $name.time.crf
	rm $name.trigger.svm
	rm $name.trigger.svmpred
	rm $name.trigger.tmp
	rm $name.type.svm
	rm $name.type.svmpred
	rm $name.type.tmp
	rm $name.value.crf
	rm $name.evc
	rm $name.md.crf

done < $CURRENT_PATH/$INPUTS

echo "Congrats! Done!"
