/* sections.ld - GNU ld Linker Script for Dragon Quest XI (3DS, CTR-P-BTZJ) */
OUTPUT_FORMAT("elf32-littlearm")
OUTPUT_ARCH(arm)
ENTRY(_start)

MEMORY
{
    FLASH       (rx)  : ORIGIN = 0x00100000, LENGTH = 0x0062403C  /* .text code: 6,438,972 B */
    PAD_TEXT    (rx)  : ORIGIN = 0x0072403C, LENGTH = 0x00000FC4  /* Text tail pad: 4,036 B */
    RODATA      (r)   : ORIGIN = 0x00725000, LENGTH = 0x00075A18  /* .rodata: 481,816 B */
    PAD_RODATA  (r)   : ORIGIN = 0x0079AA18, LENGTH = 0x000005E8  /* Rodata tail pad: 1,512 B */
    DATA        (rw)  : ORIGIN = 0x0079B000, LENGTH = 0x00027D24  /* .data: 163,108 B */
    PAD_DATA    (rw)  : ORIGIN = 0x007C2D24, LENGTH = 0x000002DC  /* Data tail pad: 732 B */
    BSS         (rw)  : ORIGIN = 0x007C3000, LENGTH = 0x00076BC0  /* .bss in RAM: 486,336 B */
}

SECTIONS
{
    .text :
    {
        __text_start__ = .;
        KEEP(*(.text.startup))
        KEEP(*(.text.init))
        *(.text)
        *(.text.*)
        . = ALIGN(4);
        __text_end__ = .;
    } > FLASH

    .text_tail :
    {
        /* Zero padding to complete 4096-byte page boundary (4,036 B) */
        FILL(0x00)
        . = ORIGIN(PAD_TEXT) + LENGTH(PAD_TEXT);
    } > PAD_TEXT

    .rodata :
    {
        __rodata_start__ = .;
        *(.rodata)
        *(.rodata.*)
        . = ALIGN(4);
        __rodata_end__ = .;
    } > RODATA

    .rodata_tail :
    {
        /* Zero padding to complete 4096-byte page boundary (1,512 B) */
        FILL(0x00)
        . = ORIGIN(PAD_RODATA) + LENGTH(PAD_RODATA);
    } > PAD_RODATA

    .data :
    {
        __data_start__ = .;
        *(.data)
        *(.data.*)
        . = ALIGN(4);
        __data_end__ = .;
    } > DATA

    .data_tail :
    {
        /* Zero padding to complete 4096-byte page boundary (732 B) */
        FILL(0x00)
        . = ORIGIN(PAD_DATA) + LENGTH(PAD_DATA);
    } > PAD_DATA

    .bss (NOLOAD) :
    {
        __bss_start__ = 0x007C2D24;  /* CRT InitBss boundary */
        *(.bss)
        *(.bss.*)
        *(COMMON)
        . = ALIGN(4);
        __bss_end__ = 0x008398E4;    /* CRT InitBss boundary */
    } > BSS

    /DISCARD/ :
    {
        *(.comment)
        *(.note*)
        *(.ARM.attributes)
    }
}
