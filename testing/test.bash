#!/bin/bash

# How to call this script:
#     bash test.bash "FOLDER" 
#     FOLDER is a folder such as - /proju/wrf-chem/software/ran-2-wrf/

echo "THE FOLDER THAT CONTAINS THE WRF OUTPUT IS"
echo $1
echo " "

input_folder=$1
cd $input_folder
#pwd
#ls

#get the output folder names
folders="output*"

#get the folders where the run output is
folder1=$folders[1]
folder2=$folders[2]

#get the full name of the folders
full_name1="$folder1/DONE*"
full_name2="$folder2/DONE*"

#checking the full name of the folders
echo "PLOTTING WRF OUTPUT FROM THE FOLDERS"
echo $input_folder$full_name1
echo $input_folder$full_name2
echo " "

#go into each wrf output folder and concatenate the files into one wrfout file
folder=$input_folder$full_name1
cd $folder
echo "CONCATENATE FILES IN"
pwd
echo ""
echo "WORKING ON: ncrcat wrfout_d01_????-??-??_??\:??\:?? wrfout_d01.nc"
ncrcat wrfout_d01_????-??-??_??\:??\:?? wrfout_d01.nc 

folder=$input_folder$full_name2
cd $folder
echo "CONCATENATE FILES IN"
pwd
echo ""
echo "WORKING ON: ncrcat wrfout_d01_????-??-??_??\:??\:?? wrfout_d01.nc"
ncrcat wrfout_d01_????-??-??_??\:??\:?? wrfout_d01.nc 




