#include "ws2812b.h"


// ��0��
void Set0Code(void)
{
    GPIOA_SetBits(GPIO_Pin_13); // ����֡��λ�ź�
    __nop();
    __nop();
    GPIOA_ResetBits(GPIO_Pin_13); // ����֡��λ�ź�
    //       NOP();
}
// ��1��
void Set1Code(void)
{
    GPIOA_SetBits(GPIO_Pin_13); // ����֡��λ�ź�
    __nop();
    __nop();
    __nop();
    __nop();
    __nop();
    __nop();
    __nop();
    __nop();
    GPIOA_ResetBits(GPIO_Pin_13); // ����֡��λ�ź�
}
// ��һ������
void SendOnePix(unsigned char buf[])
{
    unsigned char i, j;
    unsigned char temp;

    for (j = 0; j < 3; j++) {
        temp = buf[j];
        for (i = 0; i < 8; i++) {
            if (temp & 0x80)        //�Ӹ�λ��ʼ����
                    {
                Set1Code();
            } else                //���͡�0����
            {
                Set0Code();
            }
            temp = (temp << 1);      //����λ
        }
    }
}
