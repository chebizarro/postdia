#!/bin/bash
#   Postgres SQL import export goodness
#   Copyright (C), 2013 Chris Daley <chebizarro@gmail.com>
#
#    This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 2 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program; if not, write to the Free Software
#   Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#
#   This is the install script for the PostDia script
#
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
