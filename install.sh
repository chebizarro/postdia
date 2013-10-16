#!/bin/bash
#autor:		Chris Daley <chebizarro@gmail.com>
#description:	This is the install script for the PostDia script
#
#      :$$$$$I: . +$$$$$$$$$77$$$+       
#    $7 .      :$I .     ,$$..  . I$.    
#   $         ,$            7$      $?.  
# .$~         $              .$      $   
#  $         I?               ,$     $.  
#  $         $                 +7.   $   
#  $         $I$$$$=.      .$$?I$   ,$.  
#  $,       .$  .$7$.      $.+:,$  .7=   
#  =7        $     ??      $,  =I   $    
#  .$        $     ~7      ~$  =I .I?    
#   $,      .$.    =7       $~ ,$..$     
#   :$.     ,$.    $:        $..$ $.     
#    $.      $    :$         .$+7$~      
#    :$       $~  $           ,$7?.      
#     $,      $7$$$I          .7$. .~?   
#      $    ,$.. $: $         $   . I$   
#      .$, 7$I$7:  7$        .$$$$$+     
#       ..~ . 7$$$7 $        :$.         
#                   $        ??          
#                   $       .$:          
#                   $.       $           
#                   7~      .$           
#                   .$      $,           
#                     $$$$$I             
#                     .   
                     
if [ `id -g` -ne 0 ]
then
  echo "Usage:  ./$0 root group"
  exit $E_BADARGS
fi


#dia plugins
plugins=(postgres)
for plugin in ${plugins[@]}
do
	echo "compiling and copying plugin " $plugin
	chmod 644 ./src/plugins/$plugin.py
	rm -f /usr/share/dia/python/$plugin.py /usr/share/dia/python/$plugin.py
	cp ./src/plugins/$plugin.py /usr/share/dia/python/$plugin.py
	python -m compileall /usr/share/dia/python/$plugin.py
	chmod 644 /usr/share/dia/python/$plugin.py*
done;

zenity --info --text="The installation has completed successfully"
