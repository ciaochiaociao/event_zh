#!/bin/bash

set -e

#PROJECT_PATH=/workspace/EEtask/Chinese/event_zh/SinoCoreferencer
# set -x
# PROJECT_PATH=$EE_HOME/event_zh/SinoCoreferencer
PROJECT_PATH=$SINO_HOME
# set +x
#PROJECT_PATH="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
# STANFORD_CORENLP=$PROJECT_PATH/stanford-corenlp-full-2014-08-27
CRF=$PROJECT_PATH/CRF++-0.58
SVMMULTI=$PROJECT_PATH/svm_multiclass
MAXENT=$PROJECT_PATH/maxent/src/opt
SVMLIGHT=$PROJECT_PATH/svm_light
set -x
name=$(realpath $1)  # file that stores all filepaths to be extracted: test

echo $name > temp_path_file
path_file=temp_path_file
set +x
EVPROPS=-Xmx2g

# error handling
cleanup() {
echo "Cleaning..."
set +e
# name=$(eval echo $line)  # filelist: .../SinoCoreferencer/data/doc, ...
#rm $name
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

}
trap cleanup EXIT

#CORENLP_IP="http://140.109.19.190:9000"

set -x
#CORENLP_FULLURL="$CORENLP_IP/?properties={\"outputFormat\":\"xml\",\"annotators\":\"tokenize,ssplit,pos,ner,parse\",\"ssplit.boundaryTokenRegex\":\"[。]|[!?！？]+\",\"pipelineLanguage\":\"zh\"}"

CORENLP_FULLURL=$CORENLP_IP'/?properties={"outputFormat":"xml","annotators":"tokenize,ssplit,pos,ner,parse","ssplit.boundaryTokenRegex":"[。]|[!?！？]+","pipelineLanguage":"zh"}'
set +x
# call stanford parser
echo "Call Stanford CoreNLP..."

set -x
# name=$1 # read file .../SinoCoreferencer/data/doc
wget --post-file $name ${CORENLP_FULLURL} -O - > $name.xml
wget --post-file $name ${CORENLP_FULLURL} -O - > $name.json
set +x

# run mention detection
echo "Run entity mention detection..."
cd $PROJECT_PATH
set -x
java $EVPROPS -cp $PROJECT_PATH/entity.jar MentionDetection/MentionDetectionEndToEnd $path_file
set +x

set -x
cd $CRF
# test crf
# name=$1
./crf_test -m $PROJECT_PATH/model/md.model $name.md.tmp > $name.md.crf

# run time detection
./crf_test -m $PROJECT_PATH/model/time.model $name.md.tmp > $name.time.crf

# run value detection
./crf_test -m $PROJECT_PATH/model/value.model $name.md.tmp > $name.value.crf
set +x

echo "Run entity typing & subtyping..."
# run entity typing & subtyping
cd $PROJECT_PATH
java $EVPROPS -cp $PROJECT_PATH/entity.jar SVMSemantic/EntitySemanticEndToEnd $path_file

cd $SVMMULTI
# name=$1
./svm_multiclass_classify $name.type.svm $PROJECT_PATH/model/multiType.model $name.type.svmpred 1>&-
./svm_multiclass_classify $name.type.svm $PROJECT_PATH/model/multiSubType.model $name.subtype.svmpred 1>&-

cd $PROJECT_PATH
java $EVPROPS -cp $PROJECT_PATH/entity.jar SVMSemantic/ExplainSemanticType $path_file 1>&-



# run entity coreference
echo "Run entity coreference..."
cd $PROJECT_PATH
java $EVPROPS -cp $PROJECT_PATH/coref.jar ace/rule/RuleCoref $path_file

echo "Run event trigger identification..."
# run event extraction
cd $PROJECT_PATH
java $EVPROPS -cp $PROJECT_PATH/event.jar event/trigger/JointTriggerEndToEnd $path_file

cd $SVMMULTI
# name=$1
./svm_multiclass_classify $name.trigger.svm $PROJECT_PATH/model/JointTriggerModel $name.trigger.svmpred 1>&-

cd $PROJECT_PATH

java $EVPROPS -cp $PROJECT_PATH/event.jar event/trigger/ExplainTrigger $path_file

echo "Run event argument identification..."

java $EVPROPS -cp $PROJECT_PATH/event.jar event/argument/JointArgumentEndToEnd $path_file

cd $SVMMULTI
# name=$1
./svm_multiclass_classify $name.arg.svm $PROJECT_PATH/model/argumentJointModel $name.arg.svmpred 1>&-

cd $PROJECT_PATH
java $EVPROPS -cp $PROJECT_PATH/event.jar event/argument/ExplainArg $path_file

echo "Run event attributes classification..."
# run event attribute classification
java $EVPROPS -cp $PROJECT_PATH/entity.jar event/attribute/EventAttriEndToEndTest tense $path_file
java $EVPROPS -cp $PROJECT_PATH/entity.jar event/attribute/EventAttriEndToEndTest polarity $path_file
java $EVPROPS -cp $PROJECT_PATH/entity.jar event/attribute/EventAttriEndToEndTest modality $path_file
java $EVPROPS -cp $PROJECT_PATH/entity.jar event/attribute/EventAttriEndToEndTest genericity $path_file

cd $MAXENT
# name=$1  # filelist: .../SinoCoreferencer/data/doc, ...
./maxent -p $name.polarity.fea -m $PROJECT_PATH/model/polarityModel --detail -o $name.polarity.pred 1>&-
./maxent -p $name.modality.fea -m $PROJECT_PATH/model/modalityModel --detail -o $name.modality.pred 1>&-
./maxent -p $name.genericity.fea -m $PROJECT_PATH/model/genericityModel --detail -o $name.genericity.pred 1>&-
./maxent -p $name.tense.fea -m $PROJECT_PATH/model/tenseModel --detail -o $name.tense.pred 1>&-

cd $PROJECT_PATH
java $EVPROPS -cp $PROJECT_PATH/entity.jar event.attribute.ExplainAttribute $path_file

cd $PROJECT_PATH
echo "Run event coreference..."
# run event coreference
java $EVPROPS -cp $PROJECT_PATH/coref.jar ace/event/coref/MaxEntTestEnd2End $path_file 1>&-

cd $SVMLIGHT
# name=$1  # filelist: .../SinoCoreferencer/data/doc, ...
./svm_classify $name.evc.svm $PROJECT_PATH/model/coref.model0 $name.evc.pred 1>&-

cd $PROJECT_PATH
java $EVPROPS -cp $PROJECT_PATH/coref.jar ace/event/coref/MakeCluster $path_file 1>&-


echo "Congrats! Done!"
