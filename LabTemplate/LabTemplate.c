/* ENGR-2350 Fall 2020
 * SIMULATOR TEMPLATE LAB
 *
 * Replace above with your name and
 * description of code
 * */

#define STUDENT_NAME   "REPLACE_WITH_YOUR_NAME"     // Only used in this template (leave the quotes!!!)
#define RIN            REPLACE_WITH_YOUR_RIN        // Used to produce simulation variations

//#define NO_SIM                 // Uncomment to run program without simulator connection
//#define PRINTTOFILE "FILENAME.csv"    // Uncomment to print to file

//////////////
// Includes //
//////////////

//#include<c8051_SDCC.h>       // We would use this file if we were actually in the lab.
#include "C8051_SIM.h"         // This file allows us to mimic the microcontroller functionality
#include<stdio.h>               // Add terminal input/output support
#include<stdlib.h>              // Standard C functions library
#include<stdint.h>              // Alternative definitions of integer variables

/////////////////////////
// Function prototypes //
/////////////////////////
void count_to(unsigned int limit);

///////////////////
// sbit support: // (SIM SPECIFIC)
///////////////////
//__sbit __at 0xB1 PB;  // We would use this format if in the lab
#define PB  P3_1        // We will use this format for the simulator

//////////////////////
// Global variables //
//////////////////////

unsigned char counts = 0;   // A counting variable

///////////////////
// Main Function //
///////////////////

void main(void){
    // Local variables
    unsigned int loops = 0;
    unsigned char command = 0;
    Sys_Init();
    // Put initializations here

    // Put any non-looping start-up code here (still initializations really)
    printf("Student's Name: %s\r\n",STUDENT_NAME);
    printf("Student's RIN:  %u\r\n",RIN);
    printf("\r\n\n");

    while(1){
        Sim_Update();   // This function synchronizes the simulation and this program
                        // Sim_Update() needs to be called in EVERY LOOP
                        // If we weren't using the simulation, we wouldn't need to do this.
        printf("Press '1' to count to 30, Press '2' to count to 300, press 'q' to quit: ");    // Print instructions
        command = getchar();    // Get user input
        if(command == 'q'){
            break;
        }else if(command == '1'){
            counts = 0;
            count_to(30);
        }else if(command == '2'){
            counts = 0;
            count_to(300);
        }else{
            printf("\r\nunknown input: %c\r\n\n",command);
            continue;
        }
        loops++;
        printf("Times we've counted: %u\r\n\n",loops);
    }
}

/////////////////////
// Other Functions //
/////////////////////

void count_to(unsigned int limit){
    unsigned int itr = 0;
    printf("Iteration\tCounts (DEC)\tCounts (HEX)\r\n");
    for(itr=0;itr<=limit;itr++){
        Sim_Update();   // Called in EVERY LOOP!!!!
        printf("%u\t%u\t0x%X\r\n",itr,counts,counts);
        counts++;
    }
}

////////////////////////
// Interrupt Routines //
////////////////////////

// Fill in these functions as needed
//void Timer_0_ISR(){}
//void Timer_1_ISR(){}
//void PCA_ISR(){}
