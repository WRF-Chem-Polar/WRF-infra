# Debugging WRF-Chem code

## Some useful tips for debugging WRF-Chem code:

1. First, increase the debug_level option in the namelist to get more print statements in the rsl files. Increasing the value of debug_level will 
give an increasing amount of print statements. To get the maximum number of print statements, increase this value to a very high number (e.g. 5000).

2. Manually add WRITE statements in the .F files and recompile the code. The following is an example of printing chemical concentration for a specific
grid cell in the chem_driver routine (the modified chem_driver.F is also available in this repository). This code loops over the grid cells and 
prints the chemical concentration for Br in the grid cell i=10, j=25, and k=1:
```
do i=ips,ipe
    do j=jps,jpe
        if ( i==10 .and. j==25) then
            write(*,*) "THIS IS AN EXAMPLE PRINT STATEMENT FOR BR ", chem(i,1,j,p_Br)
        endif
    enddo
enddo
```

3. If modifications are made inside the chem/ folder only, no need to do a full clean compile. If Registry or KPP is modified, a full compile is needed.

4. Whenever modifying the code, modify the .F files, not the .f90 which are automatically generated upon compilation. Any change to .f90 files will be lost.
