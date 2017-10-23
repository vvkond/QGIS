/*
C --- MODULE NUMBER:  833010
C
C
CA  NAME:      sqlpas
CA
CA
CA  FUNCTION:  Generate a password to connect to a database server
CA
CA
CA  APPLICATION/SUBSYSTEM:  Dynamic SQL Interface (sql) CONTROLLED
CA
CA
C   AUTHOR:    J.A.Sharp
C
C
CA  LINKAGE:   char *sqlpas ( host, server, database )
CA
CA
CA  ARGUMENT
CA    NAME      USE   TYPE       DESCRIPTION
CA  --------    ---   ----       -----------
CA  host         I    char *     Pointer to host name string
CA  server       I    char *     Pointer to server name string
CA  database     I    char *     Pointer to database name string
CA  return       O    password * Pointer to connect password: NULL = Failure
CA
CA
CA  TABLE NAME                 USE   DESCRIPTION
CA  ------------------------   ---   -----------
CA
CA
CA  NOTES:  none
CA
CA
CA  RESTRICTIONS:  none
CA
CA
C   PORTABILITY:   DEPENDENT
C
C
C   REVISED:
C
C   10MAY95  JAS  Original version
C   22SEP95  MDK  Another fix to this password function Arrgh!!!!!!
C   25JAN96  AJP  SCR13223 : ANSI conversion.
C   18MAR04  RMY  SCR 19009 Add tigdef.h
C
C
C-------------------------------------------------------------------
C   Copyright (C) 1995-2004 Tigress Limited
C   All rights reserved
C-------------------------------------------------------------------
C
*/

#ifndef lint
static char sccsid[] = "%Z% %M% %I% %E%" ;
#endif

#include <tigress/tigdef.h>
#include <tigress/sql.h>

static int hash ( char * key )
{
    char *p;
    unsigned int h= 0;
    int g;
    for (p = key; *p!= 0; p++)
    {
        h = (h << 4) + (*p);
        if ( (g = h&0xf0000000) != 0 )
        {
            h = h ^ (g >> 24);
            h = h ^g;
        }
    }
    return h % 52;
}

/*----------------------------------------------------------------------------*/

extern char *sqlpas ( const char *host,
                      const char *server,
                      const char *database )
{
    static char  password  [64];    /* store for result */
           char  buf      [100];
           char  t_host    [50];
           char  t_server  [50];
           char  t_database[50];
           int   len,
                 i;
    char letters[] = "QRSTUVWXYZabcdetuvwxyzABCDEFGHIJKLMNOPfghijklmnopqrs";
    static char input[64];

    /*  Determine an eight character password from the host, server */
    /*  & database names. A host name less than two does not work.  */

    strcpy( t_host, host );

    while ( strlen( t_host ) < 2 ) strcat( t_host, "X" );

    /* A project name less than three does not work */

    strcpy( t_server, server );

    while ( strlen( t_server ) < 3 ) strcat( t_server, "Y" );

    /* The project name will change mostly at the end - use these to fill out */

    len = strlen( database );

    /* copy to temp - & check all are lower case */

    for ( i=0; i<len+1; i++ )
        t_database[i] = tolower( database[i] );

    while ( strlen( t_database ) < 8 )
    {
        for ( i=len-1; i >=0 ; i-- )
             t_database[len++] = t_database[i];
        t_database[len] = 0;
    }
    t_database[len] = 0;

    /* project name uses 4 letters - ie 0,2,5,7 */

    strcpy( buf, t_database );

    buf[1] = t_server [0];    /* server uses 2 letters 1 and 3 */
    buf[3] = t_server [2];

    buf[4] = t_host [1];    /* host uses 2 letters two and two! */
    buf[6] = t_host [1];

    buf[8] = 0;

/*  strcpy ( password, crypt(buf,"js") ) ; */

    len = strlen(buf);
    strcpy(input, buf);

    for (i = 0 ; i<strlen(buf); i++)
    {
        password[i] = letters[hash(&input[i])];
        input[len + i ] = input[i];
        input[len + i + 1 ] = 0;
    }
    password[i] = 0;

    /* remove any dots or slashes */

    for ( i=0; i<strlen(password);i++  )
    {
        if ( password[i] == '.' )
            password[i] = 'r';
        else if ( password[i] == '/' )
            password[i] = 'a';
    }

    /* hack for numbers */

         if ( password[2] == '0' ) password[2] = 'A';
    else if ( password[2] == '1' ) password[2] = 'B';
    else if ( password[2] == '2' ) password[2] = 'C';
    else if ( password[2] == '3' ) password[2] = 'D';
    else if ( password[2] == '4' ) password[2] = 'E';
    else if ( password[2] == '5' ) password[2] = 'F';
    else if ( password[2] == '6' ) password[2] = 'G';
    else if ( password[2] == '7' ) password[2] = 'H';
    else if ( password[2] == '8' ) password[2] = 'I';
    else if ( password[2] == '9' ) password[2] = 'J';

    password[10] = 0;  /* ie 8 long */

    return( &password[0] );
}

